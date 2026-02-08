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
        # Optimization: Only retrain if the project changed or model is empty
        if self.ml_model.boq_df is not None and not self.ml_model.boq_df.empty:
            # Check a sample item or count? For now, we assume if boq_df exists, 
            # it might be the same. A better check would be project_id matching.
            return
            
        items = self.db.query(BOQItem).filter(BOQItem.project_id == project_id).all()
        self.ml_model.fit_boq(items)

    def load_boq(self, file_path, project_id):
        try:
            items = []
            
            # Helper to clean numeric values
            def clean_num(val):
                if pd.isna(val) or val == '': return 0.0
                try:
                    s = str(val).replace(',', '').replace('rs.', '').replace('rs', '').strip()
                    # Handle parenthesis for negative if any or space-separated numbers
                    s = s.split()[0] if s else '0'
                    return float(s)
                except: return 0.0

            # Logic for Excel (.xlsx)
            if file_path.lower().endswith('.xlsx') or file_path.lower().endswith('.xls'):
                xl = pd.ExcelFile(file_path)
                for sheet_name in xl.sheet_names:
                    # Skip summary/application sheets if named specifically
                    if sheet_name.lower() in ['application', 'summary', 'mat @ site']: continue
                    
                    df_raw = pd.read_excel(xl, sheet_name=sheet_name, header=None)
                    
                    # Find header row - search up to 40 rows
                    header_idx = -1
                    for i, row in df_raw.head(40).iterrows():
                        row_str = " ".join(str(v).lower() for v in row if pd.notna(v))
                        # Aggressive keywords
                        if any(k in row_str for k in ['desc', 'qty', 'unit', 'rate', 'amount', 'item']):
                            header_idx = i
                            break
                    
                    if header_idx != -1:
                        df = pd.read_excel(xl, sheet_name=sheet_name, skiprows=header_idx)
                        df.columns = [str(c).strip().lower() for c in df.columns]
                    elif 'bill' in sheet_name.lower():
                        # Fallback: Assume row 10-15 might contain headers if not found, 
                        # or just assume position if it's a Bill sheet
                        df = df_raw.iloc[10:].copy()
                        df.columns = [f"col_{i}" for i in range(len(df.columns))]
                    else:
                        continue
                    
                    # Smart Column Mapping
                    def find_col(keywords, cols):
                        for c in cols:
                            if any(k in c for k in keywords):
                                return c
                        return None

                    cols = df.columns
                    col_map = {
                        'item': find_col(['item', 'ref', 'no'], cols) or (cols[0] if len(cols) > 0 else None),
                        'description': find_col(['description', 'desc', 'work'], cols) or (cols[1] if len(cols) > 1 else None),
                        'unit': find_col(['unit', ' un'], cols) or (cols[2] if len(cols) > 2 else None),
                        'qty': find_col(['qty', 'quantity', 'quantity'], cols) or (cols[3] if len(cols) > 3 else None),
                        'rate': find_col(['rate', 'price'], cols) or (cols[4] if len(cols) > 4 else None),
                        'amount': find_col(['amount', 'total', 'total amount'], cols) or (cols[len(cols)-1] if len(cols) > 0 else None)
                    }

                    for _, row in df.iterrows():
                        desc_col = col_map['description']
                        if not desc_col or pd.isna(row[desc_col]): continue
                        
                        desc_val = str(row[desc_col]).strip()
                        # Skip header repetitions or empty rows
                        if not desc_val or desc_val.lower() in ['description', 'desc', 'work']: continue
                        if len(desc_val) < 3: continue

                        items.append(BOQItem(
                            project_id=project_id,
                            item_number=str(row.get(col_map['item'], '')),
                            description=desc_val,
                            unit=str(row.get(col_map['unit'], '')),
                            quantity=clean_num(row.get(col_map['qty'], 0)),
                            rate=clean_num(row.get(col_map['rate'], 0)),
                            amount=clean_num(row.get(col_map['amount'], 0))
                        ))

            # Backward compatibility / Fallback for CSV
            else:
                try:
                    df = pd.read_csv(file_path, encoding='utf-8', header=None)
                except UnicodeDecodeError:
                    df = pd.read_csv(file_path, encoding='latin1', header=None)

                header_idx = -1
                for i, row in df.head(30).iterrows():
                    row_str = " ".join(str(v).lower() for v in row if pd.notna(v))
                    if 'desc' in row_str or 'qty' in row_str:
                        header_idx = i
                        break
                
                df = pd.read_csv(file_path, encoding='utf-8', skiprows=header_idx) if header_idx >= 0 else df
                df.columns = [str(c).strip().lower() for c in df.columns]
                
                def find_col(keywords, cols):
                    for c in cols:
                        if any(k in c for k in keywords):
                            return c
                    return None

                col_map = {
                    'item': find_col(['item', 'ref', 'no'], df.columns),
                    'description': find_col(['description', 'desc', 'work'], df.columns),
                    'unit': find_col(['unit'], df.columns),
                    'qty': find_col(['qty', 'quantity'], df.columns),
                    'rate': find_col(['rate', 'price'], df.columns),
                    'amount': find_col(['amount', 'total'], df.columns)
                }

                for _, row in df.iterrows():
                    desc_col = col_map['description']
                    if not desc_col or pd.isna(row[desc_col]): continue
                    items.append(BOQItem(
                        project_id=project_id,
                        item_number=str(row.get(col_map['item'], '')),
                        description=str(row[desc_col]),
                        unit=str(row.get(col_map['unit'], '')),
                        quantity=clean_num(row.get(col_map['qty'], 0)),
                        rate=clean_num(row.get(col_map['rate'], 0)),
                        amount=clean_num(row.get(col_map['amount'], 0))
                    ))
            
            if items:
                self.db.add_all(items)
                self.db.commit()
                self.train_model(project_id)
            return len(items)
        except Exception as e:
            print(f"Error loading BOQ: {e}")
            import traceback
            traceback.print_exc()
            return 0

    def load_rate_breakdown(self, file_path, project_id):
        """
        Specialized parser for nested CSV Rate Breakdowns.
        Iterates row by row to find item headers and categorized subtotals.
        """
        try:
            try:
                df = pd.read_csv(file_path, encoding='utf-8', header=None)
            except UnicodeDecodeError:
                df = pd.read_csv(file_path, encoding='latin1', header=None)

            items = []
            current_ref = None
            current_desc = None
            costs = {'mat': 0.0, 'lab': 0.0, 'plant': 0.0, 'total': 0.0}

            def clean_val(v):
                if pd.isna(v): return 0.0
                try: 
                    return float(str(v).replace(',', '').strip())
                except: return 0.0

            for i, row in df.iterrows():
                row_list = [str(v).strip() for v in row if pd.notna(v)]
                row_str = " ".join(row_list).lower()

                # 1. Detect Item Header (e.g., "2A/05 Filling with...")
                col0 = str(row[0]).strip() if pd.notna(row[0]) else ""
                if col0 and any(char.isdigit() for char in col0) and '/' in col0:
                    # Save previous item if exists
                    if current_ref and costs['total'] > 0:
                        items.append(RateBreakdown(
                            project_id=project_id, item_ref=current_ref, description=current_desc,
                            material_cost=costs['mat'], labor_cost=costs['lab'], 
                            plant_cost=costs['plant'], total_rate=costs['total']
                        ))
                    
                    current_ref = col0
                    current_desc = str(row[1]) if pd.notna(row[1]) else ""
                    costs = {'mat': 0.0, 'lab': 0.0, 'plant': 0.0, 'total': 0.0}

                # 2. Look for subtotals (using smarter value finding)
                def get_row_value(r):
                    # Try to find the first numeric-looking thing at the end of the row
                    for val in reversed(r):
                        if pd.notna(val):
                            c = clean_val(val)
                            if c > 0: return c
                    return 0.0

                if 'total material cost' in row_str:
                    costs['mat'] = get_row_value(row)
                elif 'total labour cost' in row_str:
                    costs['lab'] = get_row_value(row)
                elif 'total tools and equipment cost' in row_str:
                    costs['plant'] = get_row_value(row)
                elif 'total gross unit rate' in row_str:
                    costs['total'] = get_row_value(row)

            # Last item
            if current_ref and costs['total'] > 0:
                items.append(RateBreakdown(
                    project_id=project_id, item_ref=current_ref, description=current_desc,
                    material_cost=costs['mat'], labor_cost=costs['lab'], 
                    plant_cost=costs['plant'], total_rate=costs['total']
                ))

            if items:
                self.db.add_all(items)
                self.db.commit()
            return len(items)
        except Exception as e:
            print(f"Error loading Rate Breakdown: {e}")
            import traceback
            traceback.print_exc()
            return 0

    def evaluate_variation(self, description_query, new_material=None, qty_change=0):
        """
        Comprehensive variation analysis combining database search and FIDIC logic.
        """
        # 1. Find the item
        similar_item = self.ml_model.find_similar_item(description_query)
        if not similar_item:
            return None

        original_rate = similar_item.get('rate', 0.0)
        original_qty = similar_item.get('quantity', 0.0)
        
        # 2. Determine New Rate (FIDIC 12.3)
        # We assume some defaults for change % if not fully specified
        qty_change_pct = (qty_change / original_qty * 100.0) if original_qty > 0 else 100.0
        amt_change_pct = (qty_change * original_rate) / 1000000.0 # Hypothetical threshold
        
        if new_material:
            # If material changed, it's likely a Star Rate
            new_rate = self.derive_star_rate(new_material)
        else:
            # Check FIDIC 12.3 thresholds
            new_rate = self.calculate_new_rate(
                similar_item['description'], 
                original_rate, 
                qty_change_pct, 
                amt_change_pct, 
                10.0 # Unit cost change pct threshold
            )

        impact = (new_rate * (original_qty + qty_change)) - (original_rate * original_qty)
        
        return {
            "item_id": similar_item['id'],
            "original_item": similar_item['description'],
            "new_item": new_material or similar_item['description'],
            "original_rate": original_rate,
            "new_rate": round(new_rate, 2),
            "cost_impact": round(impact, 2),
            "is_star_rate": new_rate != original_rate
        }

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
        Derives a new rate using ML similarity search or breakdown analysis.
        """
        similar_item = self.ml_model.find_similar_item(description)
        
        if similar_item:
            # Try to get detailed breakdown if it exists
            breakdown = self.db.query(RateBreakdown).filter(RateBreakdown.item_ref == similar_item.get('item_number')).first()
            if breakdown:
                return breakdown.total_rate
            return similar_item.get('rate', 0.0)
            
        return 0.0 # Fallback

class TimeEngine:
    def __init__(self):
        self.graph = nx.DiGraph()

    def parse_schedule(self, file_path):
        if file_path.endswith('.xml'): return self._parse_msp_xml(file_path)
        if file_path.endswith('.csv'): return self._parse_msp_csv(file_path)
        return 0

    def _parse_msp_csv(self, file_path):
        try:
            try:
                df = pd.read_csv(file_path, encoding='utf-8')
            except UnicodeDecodeError:
                df = pd.read_csv(file_path, encoding='latin1')
            
            df.columns = [str(c).replace(' ', '_').lower() for c in df.columns]
            
            # Flexible Column Mapping
            col_map = {
                'id': next((c for c in df.columns if 'task_id' in c or 'uid' in c), None),
                'name': next((c for c in df.columns if 'name' in c or 'task' in c), None),
                'duration': next((c for c in df.columns if 'duration' in c or 'dur' in c), None),
                'predecessors': next((c for c in df.columns if 'pred' in c), None)
            }
            
            for _, row in df.iterrows():
                t_id = str(row.get(col_map['id'])) if col_map['id'] else str(_)
                t_name = str(row.get(col_map['name'], f"Task {t_id}"))
                
                # Parse duration (handle "533 days")
                dur_val = row.get(col_map['duration'], 0)
                duration = 0.0
                if pd.notna(dur_val):
                    try:
                        # Extract digits only
                        s_dur = "".join(filter(str.isdigit, str(dur_val)))
                        duration = float(s_dur) if s_dur else 0.0
                    except: pass
                
                self.graph.add_node(t_id, name=t_name, duration=duration)
                
                preds = str(row.get(col_map['predecessors'], ""))
                if preds and preds != "nan":
                    # Assume comma or semicolon separated IDs
                    for p in preds.replace(';', ',').split(','):
                        p = p.strip()
                        if p: self.graph.add_edge(p, t_id)
            return len(self.graph.nodes)
        except Exception as e:
            print(f"Error parsing Excel Schedule: {e}")
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
