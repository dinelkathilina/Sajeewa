import pandas as pd
import networkx as nx
from datetime import timedelta, datetime
import math
import xml.etree.ElementTree as ET
import os
from .database import BOQItem, Project, RateBreakdown
from .ml_model import MLModel

class CostEngine:
    def __init__(self, db_session):
        self.db = db_session
        self.ml_model = MLModel()

    def train_model(self, project_id):
        items = self.db.query(BOQItem).filter(BOQItem.project_id == project_id).all()
        self.ml_model.fit_boq(items)

    def load_boq(self, file_path, project_id):
        # ... (same as before) ...
        try:
            df = pd.read_excel(file_path)
            df.columns = [c.lower() for c in df.columns]
            
            # ... (mappings) ...
            col_map = {
                'item': next((c for c in df.columns if 'item' in c), None),
                'description': next((c for c in df.columns if 'desc' in c), None),
                'unit': next((c for c in df.columns if 'unit' in c), None),
                'qty': next((c for c in df.columns if 'qty' in c or 'quantity' in c), None),
                'rate': next((c for c in df.columns if 'rate' in c or 'price' in c), None),
                'amount': next((c for c in df.columns if 'amount' in c or 'total' in c), None)
            }

            items = []
            for _, row in df.iterrows():
                if pd.isna(row[col_map['description']]): continue

                item = BOQItem(
                    project_id=project_id,
                    item_number=str(row.get(col_map['item'], '')),
                    description=str(row.get(col_map['description'], '')),
                    unit=str(row.get(col_map['unit'], '')),
                    quantity=float(row.get(col_map['qty'], 0) or 0),
                    rate=float(row.get(col_map['rate'], 0) or 0),
                    amount=float(row.get(col_map['amount'], 0) or 0)
                )
                items.append(item)
            
            self.db.add_all(items)
            self.db.commit()
            
            # Train model after loading
            self.train_model(project_id)
            
            return len(items)
        except Exception as e:
            print(f"Error loading BOQ: {e}")
            return 0

    def load_rate_breakdown(self, file_path, project_id):
        # ... (Same as before) ...
        return super_load_rate_breakdown(file_path, project_id) # Placeholder to keep existing logic
        # For brevity, I am not repeating the whole function if unchanged, 
        # but since I am replacing the whole file content or large chunk, I must provide it.
        # I'll rely on the existing load_rate_breakdown implementation logic.
        # Wait, I need to provide the full content for the replacement range.
        # To avoid error, I will re-implement load_rate_breakdown here.
        try:
            df = pd.read_excel(file_path)
            df.columns = [c.lower() for c in df.columns]
            col_map = {
                'item': next((c for c in df.columns if 'item' in c or 'ref' in c), None),
                'desc': next((c for c in df.columns if 'desc' in c), None),
                'mat': next((c for c in df.columns if 'mat' in c), None),
                'lab': next((c for c in df.columns if 'lab' in c), None),
                'plant': next((c for c in df.columns if 'plant' in c or 'equip' in c), None),
                'total': next((c for c in df.columns if 'total' in c or 'rate' in c), None),
            }
            items = []
            for _, row in df.iterrows():
                if pd.isna(row[col_map['desc']]): continue
                rb = RateBreakdown(
                    project_id=project_id,
                    item_ref=str(row.get(col_map['item'], '')),
                    description=str(row.get(col_map['desc'], '')),
                    material_cost=float(row.get(col_map['mat'], 0) or 0),
                    labor_cost=float(row.get(col_map['lab'], 0) or 0),
                    plant_cost=float(row.get(col_map['plant'], 0) or 0),
                    total_rate=float(row.get(col_map['total'], 0) or 0)
                )
                items.append(rb)
            self.db.add_all(items)
            self.db.commit()
            return len(items)
        except Exception as e:
            print(f"Error loading Rate Breakdown: {e}")
            return 0

    def calculate_new_rate(self, item_description, original_rate, qty_change_pct, amt_change_pct, unit_cost_change_pct):
        """
        Implements FIDIC 12.3 logic to determine if a new rate is applicable.
        """
        is_qty = abs(qty_change_pct) > 10.0
        is_amt = amt_change_pct > 0.01 
        is_cost = unit_cost_change_pct > 1.0

        if is_qty and is_amt and is_cost:
            return self.derive_star_rate(item_description)
        return original_rate

    def derive_star_rate(self, description):
        """
        Derives a new rate using ML similarity search.
        """
        similar_item = self.ml_model.find_similar_item(description)
        
        if similar_item:
            base_rate = similar_item.get('rate', 0)
            similar_desc = similar_item.get('description', '')
            
            # Predict productivity factor
            p_new = self.ml_model.predict_productivity(description)
            p_old = self.ml_model.predict_productivity(similar_desc)
            if p_old == 0: p_old = 1
            
            prod_factor = p_new / p_old
            
            # Apply factor to assumed Labor portion (30%)
            labor_portion = base_rate * 0.30
            material_portion = base_rate * 0.70
            
            # If productivity is lower (factor < 1), labor cost increases
            # Actually, cost is inversely proportional to productivity
            # Cost Factor = p_old / p_new
            cost_factor = p_old / p_new if p_new > 0 else 1.0
            
            adjusted_labor = labor_portion * cost_factor
            
            return material_portion + adjusted_labor
            
        return 0.0 # Need external data

class TimeEngine:
    def __init__(self):
        self.graph = nx.DiGraph()

    def parse_schedule(self, file_path):
        if file_path.endswith('.xml'): return self._parse_msp_xml(file_path)
        return 0

    def _parse_msp_xml(self, file_path):
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            for task in root.findall(".//{http://schemas.microsoft.com/project}Task") or root.findall("Task"):
                t_id = task.findtext("UID") or task.findtext("{http://schemas.microsoft.com/project}UID")
                t_name = task.findtext("Name") or task.findtext("{http://schemas.microsoft.com/project}Name")
                dur_txt = task.findtext("Duration") or task.findtext("{http://schemas.microsoft.com/project}Duration") or ""
                
                duration = 0
                if 'H' in dur_txt:
                    try: duration = float(dur_txt.replace('PT','').replace('H','').split('M')[0]) / 8.0
                    except: pass
                
                if t_id: self.graph.add_node(t_id, name=t_name, duration=duration)
                
                for pred in task.findall("PredecessorLink") or task.findall("{http://schemas.microsoft.com/project}PredecessorLink"):
                    p_uid = pred.findtext("PredecessorUID") or pred.findtext("{http://schemas.microsoft.com/project}PredecessorUID")
                    if p_uid and t_id: self.graph.add_edge(p_uid, t_id)
            return len(self.graph.nodes)
        except Exception as e:
            print(f"Error parsing MSP: {e}")
            return 0

    def calculate_project_duration(self):
        try:
            # CPM: Path length is sum of node durations.
            # NetworkX longest_path usually uses edge weights.
            # We can use a simple algorithm:
            # 1. Topologically sort.
            # 2. DP: Dist[v] = Duration[v] + max(Dist[u] for u in predecessors)
            
            if not self.graph.nodes: return 0.0
            
            dist = {}
            for node in nx.topological_sort(self.graph):
                dur = self.graph.nodes[node].get('duration', 0)
                preds = list(self.graph.predecessors(node))
                if not preds:
                    dist[node] = dur
                else:
                    dist[node] = dur + max(dist[p] for p in preds)
            
            return max(dist.values()) if dist else 0.0
        except Exception as e:
            print(f"CPM Error: {e}")
            return 0.0

    def calculate_eot(self, affected_task_name_query, extra_duration_days):
        """
        Calculates Extension of Time by comparing project duration before and after delay.
        """
        # Find task by name (fuzzy match)
        target_node = None
        for node, data in self.graph.nodes(data=True):
            if affected_task_name_query.lower() in data.get('name', '').lower():
                target_node = node
                break
        
        if not target_node:
            return None, "Task not found relevant to query."

        # Original Duration
        original_duration = self.calculate_project_duration()
        
        # Apply Delay temporarily
        old_task_duration = self.graph.nodes[target_node]['duration']
        self.graph.nodes[target_node]['duration'] += extra_duration_days
        
        # New Duration
        new_duration = self.calculate_project_duration()
        
        # Revert change
        self.graph.nodes[target_node]['duration'] = old_task_duration
        
        delay_impact = new_duration - original_duration
        
        return delay_impact, f"Task '{self.graph.nodes[target_node]['name']}' is on the critical path." if delay_impact > 0 else f"Task '{self.graph.nodes[target_node]['name']}' has float. No EOT required."
