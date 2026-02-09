import pandas as pd
import networkx as nx
from datetime import timedelta, datetime
import math
import xml.etree.ElementTree as ET
import os
from .storage_manager import storage_manager
from .ml_model import MLModel

class CostEngine:
    def __init__(self, storage=None):
        self.storage = storage or storage_manager
        self.ml_model = MLModel()

    def train_model(self, project_id):
        project = self.storage.get_project(project_id)
        if not project: return
        self.ml_model.fit_boq(project.get("boq_items", []))

    def validate_boq_file(self, file_path):
        """
        Validates the BOQ file structure and content.
        Returns: {'valid': bool, 'errors': [str], 'metadata': dict}
        """
        errors = []
        metadata = {}
        sheet_found = False
        
        try:
            if not os.path.exists(file_path):
                return {'valid': False, 'errors': ["File not found"], 'metadata': {}}

            # Logic for Excel (.xlsx)
            if file_path.lower().endswith(('.xlsx', '.xls')):
                try:
                    with pd.ExcelFile(file_path) as xl:
                        for sheet_name in xl.sheet_names:
                            if sheet_name.lower() in ['application', 'summary', 'mat @ site', 'gs', 'grand summary', 'summary of bill']: continue
                            
                            try:
                                df_raw = pd.read_excel(xl, sheet_name=sheet_name, header=None)
                            except: continue
                            
                            # Find header row
                            header_idx = -1
                            for i, row in df_raw.head(40).iterrows():
                                row_str = " ".join(str(v).lower() for v in row if pd.notna(v))
                                if any(k in row_str for k in ['desc', 'qty', 'unit', 'rate']):
                                    header_idx = i
                                    break
                            
                            if header_idx != -1:
                                df = pd.read_excel(xl, sheet_name=sheet_name, skiprows=header_idx)
                                df.columns = [str(c).strip().lower() for c in df.columns]
                                
                                # Smart Column Detection
                                required = {
                                    'description': ['description', 'desc', 'work', 'activity', 'item name'],
                                    'quantity': ['qty', 'quantity', 'amount'],
                                    'rate': ['rate', 'price', 'unit rate']
                                }
                                
                                missing = []
                                for field, keywords in required.items():
                                    found = False
                                    for col in df.columns:
                                        if any(k in col for k in keywords):
                                            found = True
                                            break
                                    if not found:
                                        missing.append(field)
                                
                                if missing:
                                    errors.append(f"Sheet '{sheet_name}': Missing columns: {', '.join(missing)}")
                                else:
                                    sheet_found = True
                                    break # valid sheet found
                except Exception as e:
                    return {'valid': False, 'errors': [f"Invalid Excel file: {str(e)}"], 'metadata': {}}
            
            elif file_path.lower().endswith('.csv'):
                # Simple CSV check with robust header detection
                try:
                    # Try UTF-8 then Latin1
                    try:
                        df_raw = pd.read_csv(file_path, header=None)
                    except UnicodeDecodeError:
                        df_raw = pd.read_csv(file_path, encoding='latin1', header=None)
                    
                    # Find header row
                    header_idx = -1
                    required_keywords = ['desc', 'qty', 'rate', 'unit', 'price', 'work']
                    for i, row in df_raw.head(20).iterrows():
                        row_str = " ".join(str(v).lower() for v in row if pd.notna(v))
                        if any(k in row_str for k in required_keywords):
                            header_idx = i
                            break
                    
                    if header_idx != -1:
                        df = pd.read_csv(file_path, skiprows=header_idx)
                    else:
                        df = pd.read_csv(file_path) # Fallback to first row
                    
                    df.columns = [str(c).strip().lower() for c in df.columns]
                    
                    required = {
                        'description': ['description', 'desc', 'work', 'activity', 'item name'],
                        'quantity': ['qty', 'quantity', 'amount'],
                        'rate': ['rate', 'price', 'unit rate']
                    }
                    
                    missing = []
                    for field, keywords in required.items():
                        found = False
                        for col in df.columns:
                            if any(k in col for k in keywords):
                                found = True
                                break
                        if not found:
                            missing.append(field)
                    
                    if missing:
                        errors.append(f"CSV missing critical columns: {', '.join(missing)}. Detected headers: {list(df.columns)}")
                    else:
                        sheet_found = True
                except Exception as e:
                     errors.append(f"Invalid CSV file processing error: {str(e)}")

            else:
                errors.append("Unsupported file format. Please upload .xlsx, .xls, or .csv")

            if not sheet_found and not errors:
                errors.append("Could not identify a valid BOQ sheet with 'Description', 'Qty', and 'Rate' headers.")

        except Exception as e:
            errors.append(f"Unexpected validation error: {str(e)}")

        return {
            'valid': sheet_found,
            'errors': [] if sheet_found else errors,
            'metadata': metadata
        }

    def load_boq(self, file_path, project_id):
        try:
            items_by_sheet = {}
            
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
                with pd.ExcelFile(file_path) as xl:
                    for sheet_name in xl.sheet_names:
                        # Skip summary/application sheets if named specifically
                        if sheet_name.lower() in ['application', 'summary', 'mat @ site', 'gs', 'grand summary', 'summary of bill']: continue
                        
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
                            df = df_raw.iloc[10:].copy()
                            df.columns = [f"col_{i}" for i in range(len(df.columns))]
                        else:
                            continue
                    
                        # Smart Column Mapping
                        cols = df.columns
                        col_map = {
                            'item': next((c for c in cols if any(k in c for k in ['item', 'ref', 'no'])), None) or (cols[0] if len(cols) > 0 else None),
                            'description': next((c for c in cols if any(k in c for k in ['description', 'desc', 'work'])), None) or (cols[1] if len(cols) > 1 else None),
                            'unit': next((c for c in cols if any(k in c for k in ['unit', ' un'])), None) or (cols[2] if len(cols) > 2 else None),
                            'qty': next((c for c in cols if any(k in c for k in ['qty', 'quantity'])), None) or (cols[3] if len(cols) > 3 else None),
                            'rate': next((c for c in cols if any(k in c for k in ['rate', 'price'])), None) or (cols[4] if len(cols) > 4 else None),
                            'amount': next((c for c in cols if any(k in c for k in ['amount', 'total'])), None) or (cols[len(cols)-1] if len(cols) > 0 else None)
                        }

                        sheet_items = []
                        for _, row in df.iterrows():
                            desc_col = col_map['description']
                            if not desc_col or pd.isna(row[desc_col]): continue
                            
                            desc_val = str(row[desc_col]).strip()
                            if not desc_val or desc_val.lower() in ['description', 'desc', 'work']: continue
                            if len(desc_val) < 3: continue

                            sheet_items.append({
                                'item_number': str(row.get(col_map['item'], '')),
                                'description': desc_val,
                                'unit': str(row.get(col_map['unit'], '')),
                                'quantity': clean_num(row.get(col_map['qty'], 0)),
                                'rate': clean_num(row.get(col_map['rate'], 0)),
                                'amount': clean_num(row.get(col_map['amount'], 0)),
                                'is_fixed_rate': 0
                            })
                        items_by_sheet[sheet_name] = sheet_items
                    return items_by_sheet

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

                csv_items = []
                for _, row in df.iterrows():
                    desc_col = col_map['description']
                    if not desc_col or pd.isna(row[desc_col]): continue
                    csv_items.append({
                        'item_number': str(row.get(col_map['item'], '')),
                        'description': str(row[desc_col]),
                        'unit': str(row.get(col_map['unit'], '')),
                        'quantity': clean_num(row.get(col_map['qty'], 0)),
                        'rate': clean_num(row.get(col_map['rate'], 0)),
                        'amount': clean_num(row.get(col_map['amount'], 0)),
                        'is_fixed_rate': 0
                    })
                items_by_sheet["General"] = csv_items
                return items_by_sheet
        except Exception as e:
            print(f"Error loading BOQ: {e}")
            import traceback
            traceback.print_exc()
            return {}

    def save_rate_breakdown_df(self, df, project_id):
        """Save a pandas DataFrame of rate breakdowns to the database"""
        try:
            items = []
            for _, row in df.iterrows():
                items.append({
                    'item_ref': str(row.get('item_ref', '')),
                    'description': str(row.get('description', 'Parsed from OCR')),
                    'material_cost': float(row.get('material_cost', 0.0)),
                    'labor_cost': float(row.get('labor_cost', row.get('rate', 0.0))),
                    'plant_cost': float(row.get('plant_cost', 0.0)),
                    'total_rate': float(row.get('total_rate', row.get('rate', 0.0)))
                })
            
            return items
        except Exception as e:
            print(f"Error saving rate breakdown dataframe: {e}")
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
            # Last item
            if current_ref and costs['total'] > 0:
                items.append({
                    'item_ref': current_ref, 'description': current_desc,
                    'material_cost': costs['mat'], 'labor_cost': costs['lab'], 
                    'plant_cost': costs['plant'], 'total_rate': costs['total']
                })

            return items
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
        rate_source = "Original Rate"
        if new_material:
            # If material changed, it's likely a Star Rate
            new_rate, rate_source = self.derive_star_rate(new_material, project_id=similar_item.get('project_id'))
            # Fallback to original rate if star rate derivation fails
            if new_rate == 0.0:
                new_rate = original_rate
                rate_source = "Original Rate (Fallback)"
        else:
            # Check FIDIC 12.3 thresholds
            new_rate, rate_source = self.calculate_new_rate(
                similar_item, 
                qty_change
            )

        impact = (new_rate * (original_qty + qty_change)) - (original_rate * original_qty)
        
        return {
            "item_id": similar_item['id'],
            "original_item": similar_item['description'],
            "new_item": new_material or similar_item['description'],
            "original_rate": original_rate,
            "new_rate": round(new_rate, 2),
            "cost_impact": round(impact, 2),
            "is_star_rate": new_rate != original_rate,
            "rate_source": rate_source
        }

    def calculate_new_rate(self, item, qty_change, unit_cost_change_pct=0.0):
        """
        Implements FIDIC 12.3 logic to determine if a new rate is appropriate.
        Rules:
        a) qty changed by > 10%
        b) (qty_change * rate) > 0.01% of Accepted Contract Amount
        c) cost per unit changed by > 1%
        d) item is not a "fixed rate item"
        """
        original_qty = item.get('quantity', 0.0)
        original_rate = item.get('rate', 0.0)
        is_fixed = item.get('is_fixed_rate', 0) == 1
        
        if is_fixed:
            return original_rate, "Original Rate"

        project = self.storage.get_project(item['project_id'])
        contract_amount = project.get("accepted_contract_amount", 0.0) if project else 0.0
        
        # Avoid division by zero
        qty_change_pct = (abs(qty_change) / original_qty * 100.0) if original_qty > 0 else 100.0
        value_change = abs(qty_change) * original_rate
        threshold_01_pct = 0.0001 * contract_amount
        
        is_qty_rule = qty_change_pct > 10.0
        is_val_rule = value_change > threshold_01_pct and contract_amount > 0
        is_cost_rule = unit_cost_change_pct > 1.0 # This would typically come from detailed breakdown analysis
        
        # FIDIC 12.3(a): New rate applies if ALL conditions (a), (b), (c) are met and (d) is not fixed
        if is_qty_rule and is_val_rule: # Simplified check for now (ignoring cost rule if not provided)
             # Try to derive from similar characters or HSR/BSR
             print(f"DEBUG: Rate re-valuation triggered for {item.get('description')}")
             return self.derive_star_rate(item['description'], project_id=item['project_id'])
             
        return original_rate, "Original Rate"

    def derive_star_rate(self, description, project_id=None):
        """
        Derives a new rate using ML similarity search, breakdown analysis,
        or searching external HSR/BSR files.
        """
        # 1. Search existing Rate Breakdowns
        similar_item = self.ml_model.find_similar_item(description)
        if similar_item:
             project = self.storage.get_project(project_id) if project_id else None
             if project:
                breakdowns = project.get("rate_breakdowns", [])
                breakdown = next((b for b in breakdowns if b['item_ref'] == similar_item.get('item_number')), None)
                if breakdown:
                    return breakdown['total_rate'], f"Breakdown ({similar_item.get('item_number', 'N/A')})"
        
        # 2. Search HSR/BSR/Quotation files
        external_rate, source = self.search_external_rates(description)
        if external_rate > 0:
            return external_rate, f"External: {source}"
            
        # 3. Fallback: ML Similarity from BOQ (if high confidence)
        if similar_item and similar_item.get('similarity', 0) > 0.8:
            return similar_item.get('rate', 0.0), f"Similar to {similar_item.get('item_number')}"
            
        # 4. Fallback: ML Regression Prediction
        pred_rate, confidence = self.ml_model.predict_rate(description)
        if pred_rate > 0 and confidence > 0.5:
            return pred_rate, f"ML Prediction (Conf: {confidence:.2f})"
            
        return 0.0, "Not Found"

    def update_variation_detail(self, project_id, variation_id, detail_id, updates):
        """
        Update a variation detail and recalculate impacts.
        updates: dict containing new_rate, new_quantity, justification, etc.
        """
        variation = self.storage.get_variation(project_id, variation_id)
        if not variation: return None
        
        detail = next((d for d in variation.get("details", []) if d["id"] == detail_id), None)
        if not detail: return None
            
        # Apply updates
        if 'new_rate' in updates:
            detail['new_rate'] = float(updates['new_rate'])
            detail['rate_source'] = "Manual Adjustment"
        if 'new_quantity' in updates:
            detail['new_quantity'] = float(updates['new_quantity'])
        if 'justification' in updates:
            detail['justification'] = updates['justification']
        if 'new_description' in updates:
            detail['new_description'] = updates['new_description']
            
        # Recalculate line impact
        val_old = (detail.get('original_quantity') or 0) * (detail.get('original_rate') or 0)
        val_new = (detail.get('new_quantity') or 0) * (detail.get('new_rate') or 0)
        detail['cost_impact'] = val_new - val_old
        
        # Save updated variation
        self.storage.update_project(project_id, {"variations": variation["variations"]})
        
        # Update Parent Variation Totals
        self.recalculate_variation_totals(project_id, variation_id)
        
        return detail

    def recalculate_variation_totals(self, project_id, variation_id):
        """Sum up all details to update variation total cost impact"""
        variation = self.storage.get_variation(project_id, variation_id)
        if not variation: return
        
        total_impact = sum(d.get('cost_impact', 0.0) for d in variation.get('details', []))
            
        variation['cost_impact'] = total_impact
        variation['updated_at'] = datetime.utcnow().isoformat()
        
        # Update variation in project
        project = self.storage.get_project(project_id)
        for i, v in enumerate(project.get("variations", [])):
            if v["id"] == variation_id:
                project["variations"][i] = variation
                break
        self.storage.update_project(project_id, {"variations": project["variations"]})

    def evaluate_variation_full(self, collected_details, project_id, session_id):
        """
        Processes a full variation evaluation based on collected details.
        """
        total_cost_impact = 0.0
        details_list = []
        
        # 2. Process Cost Impact for each affected item
        affected_items = collected_details.get('affected_items', [])
        if not isinstance(affected_items, list):
            affected_items = [affected_items]
            
        for item_desc in affected_items:
            similar = self.ml_model.find_similar_item(item_desc)
            if not similar or similar.get('similarity', 0) < 0.6:
                continue
                
            qty_change = 0.0
            qty_info = str(collected_details.get('quantity_changes', "0")).lower()
            try:
                 import re
                 match = re.search(r'([+-]?\d*\.?\d+)', qty_info)
                 if match:
                     val = float(match.group(1))
                     if any(k in qty_info for k in ['total', 'new', 'final']) and not any(k in qty_info for k in ['delta', 'increase', 'extra', 'add', 'decrease']):
                         original_qty = similar.get('quantity', 0.0)
                         qty_change = val - original_qty
                     else:
                         qty_change = val
            except: pass
            
            eval_result = self.evaluate_variation(
                item_desc, 
                new_material=collected_details.get('specification_changes'),
                qty_change=qty_change
            )
            
            if eval_result:
                detail = {
                    'id': len(details_list) + 1,
                    'boq_item_id': eval_result['item_id'],
                    'original_description': eval_result['original_item'],
                    'new_description': eval_result['new_item'],
                    'original_quantity': similar.get('quantity', 0),
                    'new_quantity': similar.get('quantity', 0) + qty_change,
                    'original_rate': eval_result['original_rate'],
                    'new_rate': eval_result['new_rate'],
                    'rate_source': eval_result['rate_source'],
                    'cost_impact': eval_result['cost_impact'],
                    'justification': f"Method: {collected_details.get('method_changes')}, Location: {collected_details.get('location_changes')}"
                }
                total_cost_impact += eval_result['cost_impact']
                details_list.append(detail)

        # 3. Process Time Impact
        time_engine = TimeEngine(storage=self.storage)
        time_impact = time_engine.evaluate_time_impact(collected_details, project_id)
        
        # 4. Create Variation In Storage
        variation_data = {
            "description": f"Variation: {collected_details.get('specification_changes', 'New Variation')}",
            "cost_impact": total_cost_impact,
            "time_impact": time_impact,
            "details": details_list
        }
        variation = self.storage.create_variation(project_id, session_id, variation_data)
        
        return {
            "variation_id": variation['id'],
            "cost_impact": total_cost_impact,
            "time_impact": time_impact,
            "details": details_list
        }

    def search_external_rates(self, description):
        """
        Searches through HSR, BSR, and Quotation files in the upload directory.
        Returns: (rate, source_filename)
        """
        upload_dir = "uploaded_files"
        if not os.path.exists(upload_dir):
            return 0.0, None
            
        for filename in os.listdir(upload_dir):
            if any(k in filename.upper() for k in ["HSR", "BSR", "QUOTATION"]):
                path = os.path.join(upload_dir, filename)
                try:
                    df = None
                    if path.endswith('.csv'):
                        try:
                            df = pd.read_csv(path, encoding='utf-8')
                        except:
                            df = pd.read_csv(path, encoding='latin1')
                    elif path.endswith(('.xlsx', '.xls')):
                        with pd.ExcelFile(path) as xl:
                            df = pd.read_excel(xl)
                    
                    if df is not None:
                        # Clean columns
                        df.columns = [str(c).strip().lower() for c in df.columns]
                        
                        # Find relevant columns
                        desc_cols = [c for c in df.columns if any(k in c for k in ['desc', 'item', 'work'])]
                        rate_cols = [c for c in df.columns if any(k in c for k in ['rate', 'price', 'unit rate'])]
                        
                        if desc_cols and rate_cols:
                            desc_col = desc_cols[0]
                            rate_col = rate_cols[0]
                            
                            # Searching for best match
                            for _, row in df.iterrows():
                                row_desc = str(row[desc_col]).lower()
                                # Simple keyword match approach
                                query_keywords = description.lower().split()
                                match_count = sum(1 for word in query_keywords if word in row_desc)
                                
                                # If more than 50% of words match
                                if match_count > (len(query_keywords) * 0.5):
                                    try:
                                        val = str(row[rate_col]).replace(',', '').strip()
                                        return float(val), filename
                                    except: continue
                except Exception as e:
                    print(f"Error searching {filename}: {e}")
        
        return 0.0, None 

class TimeEngine:
    def __init__(self, storage=None):
        self.graph = nx.DiGraph()
        self.storage = storage or storage_manager
        self.cpm_calculated = False
        from .ml_model import MLModel
        self.ml_model = MLModel()

    def estimate_activity_duration(self, description):
        """Estimate duration using ML model"""
        if hasattr(self.ml_model, 'predict_duration'):
            duration, confidence = self.ml_model.predict_duration(description)
            if duration > 0:
                return duration, confidence
        return 0.0, 0.0

    def parse_schedule(self, file_path, project_id=None):
        """Parse schedule and return internal activities"""
        self.graph.clear()
        if file_path.endswith('.xml'): 
            self._parse_msp_xml(file_path)
        elif file_path.endswith('.csv') or file_path.endswith('.xlsx'):
            self._parse_msp_csv(file_path)
        
        activities = []
        for node_id, data in self.graph.nodes(data=True):
            preds = list(self.graph.predecessors(node_id))
            activities.append({
                "activity_id": str(node_id),
                "name": data.get('name', ''),
                "duration": data.get('duration', 0.0),
                "predecessors": ','.join(preds) if preds else None
            })
        return activities

    def _parse_msp_csv(self, file_path):
        try:
            # Handle both CSV and Excel
            if file_path.endswith('.xlsx') or file_path.endswith('.xls'):
                with pd.ExcelFile(file_path) as xl:
                    df = pd.read_excel(xl)
            else:
                try:
                    df = pd.read_csv(file_path, encoding='utf-8')
                except UnicodeDecodeError:
                    df = pd.read_csv(file_path, encoding='latin1')
            
            df.columns = [str(c).replace(' ', '_').lower() for c in df.columns]
            
            # Flexible Column Mapping
            col_map = {
                'id': next((c for c in df.columns if 'task_id' in c or 'uid' in c or 'id' in c), None),
                'name': next((c for c in df.columns if 'name' in c or 'task' in c or 'activity' in c), None),
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
            print(f"Error parsing Schedule: {e}")
            import traceback
            traceback.print_exc()
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

        return []
        except Exception as e:
            print(f"Error storing activities: {e}")
            self.db.rollback()

    def calculate_cpm_full(self):
        """
        Calculate full CPM with ES, EF, LS, LF, and Float for all activities
        Returns dictionary with node_id as key and CPM data as value
        """
        if not self.graph.nodes:
            return {}
        
        try:
            # Forward pass - Calculate ES and EF
            es = {}  # Early Start
            ef = {}  # Early Finish
            
            for node in nx.topological_sort(self.graph):
                duration = self.graph.nodes[node].get('duration', 0)
                preds = list(self.graph.predecessors(node))
                
                if not preds:
                    es[node] = 0.0
                else:
                    es[node] = max(ef[p] for p in preds)
                
                ef[node] = es[node] + duration
            
            # Project duration
            project_duration = max(ef.values()) if ef else 0.0
            
            # Backward pass - Calculate LS and LF
            ls = {}  # Late Start
            lf = {}  # Late Finish
            
            # Start from the end nodes
            for node in reversed(list(nx.topological_sort(self.graph))):
                duration = self.graph.nodes[node].get('duration', 0)
                succs = list(self.graph.successors(node))
                
                if not succs:
                    lf[node] = project_duration
                else:
                    lf[node] = min(ls[s] for s in succs)
                
                ls[node] = lf[node] - duration
            
            # Calculate Float and identify critical activities
            cpm_data = {}
            for node in self.graph.nodes:
                total_float = ls[node] - es[node]
                is_critical = abs(total_float) < 0.01  # Account for floating point errors
                
                cpm_data[node] = {
                    'name': self.graph.nodes[node].get('name', ''),
                    'duration': self.graph.nodes[node].get('duration', 0),
                    'es': es[node],
                    'ef': ef[node],
                    'ls': ls[node],
                    'lf': lf[node],
                    'total_float': total_float,
                    'is_critical': is_critical
                }
                
                # Update graph node with CPM data
                self.graph.nodes[node].update({
                    'es': es[node],
                    'ef': ef[node],
                    'ls': ls[node],
                    'lf': lf[node],
                    'total_float': total_float,
                    'is_critical': 1 if is_critical else 0
                })
            
            self.cpm_calculated = True
            
            return cpm_data
            
        except Exception as e:
            print(f"CPM Calculation Error: {e}")
            import traceback
            traceback.print_exc()
            return {}

    def _update_cpm_in_storage(self, project_id, cpm_data):
        """Update CPM calculations in storage"""
        project = self.storage.get_project(project_id)
        if not project: return
        
        for node_id, data in cpm_data.items():
            for i, activity in enumerate(project.get("activities", [])):
                if activity["activity_id"] == str(node_id):
                    activity.update({
                        'early_start': data['es'],
                        'early_finish': data['ef'],
                        'late_start': data['ls'],
                        'late_finish': data['lf'],
                        'total_float': data['total_float'],
                        'is_critical': 1 if data['is_critical'] else 0
                    })
                    break
        
        self.storage.update_project(project_id, {"activities": project["activities"]})

    def identify_critical_path(self):
        """
        Identify and return the critical path activities
        Returns list of node IDs on the critical path
        """
        if not self.cpm_calculated:
            self.calculate_cpm_full()
        
        critical_activities = [
            node for node in self.graph.nodes
            if self.graph.nodes[node].get('is_critical', 0) == 1
        ]
        
        return critical_activities

    def map_variation_to_activities(self, variation_description, affected_items=None):
        """
        Map variation to affected activities based on description or BOQ items
        Returns list of activity IDs that may be affected
        """
        affected_activities = []
        
        # Simple keyword matching for now
        keywords = variation_description.lower().split()
        
        for node, data in self.graph.nodes(data=True):
            activity_name = data.get('name', '').lower()
            # Check if any keyword matches activity name
            if any(keyword in activity_name for keyword in keywords if len(keyword) > 3):
                affected_activities.append(node)
        
        return affected_activities

    def adjust_activity_duration(self, activity_id, new_duration):
        """
        Adjust activity duration and recalculate CPM
        Returns updated CPM data
        """
        if activity_id in self.graph.nodes:
            self.graph.nodes[activity_id]['duration'] = new_duration
            self.cpm_calculated = False
            return self.calculate_cpm_full()
        return None

    def calculate_project_duration(self):
        """Calculate total project duration using CPM"""
        if not self.cpm_calculated:
            cpm_data = self.calculate_cpm_full()
            if cpm_data:
                return max(data['ef'] for data in cpm_data.values())
        
        # Fallback to simple calculation
        try:
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
        Calculate Extension of Time with detailed breakdown
        Returns (eot_days, breakdown_dict)
        """
        # Find task by name (fuzzy match)
        target_node = None
        for node, data in self.graph.nodes(data=True):
            if affected_task_name_query.lower() in data.get('name', '').lower():
                target_node = node
                break
        
        if not target_node:
            return None, {"error": "Task not found relevant to query."}

        # Calculate CPM before change
        original_cpm = self.calculate_cpm_full()
        original_duration = max(data['ef'] for data in original_cpm.values())
        original_critical = self.identify_critical_path()
        
        # Apply delay
        old_task_duration = self.graph.nodes[target_node]['duration']
        self.graph.nodes[target_node]['duration'] += extra_duration_days
        self.cpm_calculated = False
        
        # Calculate CPM after change
        new_cpm = self.calculate_cpm_full()
        new_duration = max(data['ef'] for data in new_cpm.values())
        new_critical = self.identify_critical_path()
        
        # Revert change
        self.graph.nodes[target_node]['duration'] = old_task_duration
        self.cpm_calculated = False
        
        eot = new_duration - original_duration
        
        breakdown = {
            'affected_activity': {
                'id': target_node,
                'name': self.graph.nodes[target_node]['name'],
                'original_duration': old_task_duration,
                'new_duration': old_task_duration + extra_duration_days,
                'delay_added': extra_duration_days
            },
            'original_project_duration': original_duration,
            'new_project_duration': new_duration,
            'eot_days': eot,
            'is_on_critical_path': target_node in original_critical,
            'original_float': original_cpm.get(target_node, {}).get('total_float', 0),
            'critical_path_changed': set(original_critical) != set(new_critical),
            'justification': self._generate_eot_justification(
                target_node, eot, original_cpm.get(target_node, {})
            )
        }
        
        return eot, breakdown

    def generate_gantt_data(self):
        """
        Generate data for Gantt chart visualization
        Returns list of activities with start/end timing
        """
        if not self.cpm_calculated:
            self.calculate_cpm_full()
            
        gantt_data = []
        cpm = self.calculate_cpm_full() # Ensure we have latest data
        
        # Sort by Early Start
        sorted_nodes = sorted(cpm.keys(), key=lambda x: cpm[x]['es'])
        
        for node_id in sorted_nodes:
            data = cpm[node_id]
            gantt_data.append({
                'id': node_id,
                'name': data['name'],
                'start_day': data['es'],
                'end_day': data['ef'],
                'duration': data['duration'],
                'is_critical': data['is_critical'],
                'total_float': data['total_float']
            })
            
        return gantt_data

    def _generate_eot_justification(self, activity_id, eot, cpm_data):
        """Generate justification text for EOT claim"""
        activity_name = self.graph.nodes[activity_id].get('name', activity_id)
        total_float = cpm_data.get('total_float', 0)
        
        if eot > 0:
            if total_float < 0.01:
                return f"Activity '{activity_name}' is on the critical path with zero float. " \
                       f"Any delay to this activity directly impacts project completion. " \
                       f"EOT of {eot:.1f} days is justified."
            else:
                return f"Activity '{activity_name}' had {total_float:.1f} days of float. " \
                       f"The delay exceeded the available float, resulting in EOT of {eot:.1f} days."
        else:
            return f"Activity '{activity_name}' has {total_float:.1f} days of float. " \
                    f"The delay is absorbed within the float. No EOT required."

    def evaluate_time_impact(self, collected_details, project_id):
        """
        Evaluate time impact (EOT) based on affected activities and duration adjustments.
        """
        project = self.storage.get_project(project_id)
        if not project: return 0
        
        activities = project.get("activities", [])
        if not activities:
            return 0
            
        self.graph.clear()
        for act in activities:
            self.graph.add_node(act['activity_id'], name=act['name'], duration=act['duration'] or 0.0)
            if act.get('predecessors'):
                preds_raw = act['predecessors'].replace(';', ',')
                for p in preds_raw.split(','):
                    if p.strip() and p.strip() in self.graph:
                        self.graph.add_edge(p.strip(), act['activity_id'])
        
        # 2. Baseline CPM
        baseline_results = self.calculate_cpm_full()
        baseline_duration = max([v['ef'] for v in baseline_results.values()]) if baseline_results else 0
        
        # 3. Apply Adjustments
        affected_act_names = collected_details.get('affected_activities', [])
        if not isinstance(affected_act_names, list):
            affected_act_names = [affected_act_names]
            
        qty_change_pct = 0.0
        qty_info = str(collected_details.get('quantity_changes', "0"))
        try:
            import re
            match = re.search(r'([+-]?\d*\.?\d+)', qty_info)
            if match:
                val = float(match.group(1))
                qty_change_pct = val if val < 200 else (val / 100.0) 
        except: pass
        
        applied_count = 0
        for act_name in affected_act_names:
            if not act_name: continue
            best_match = None
            for node_id, data in self.graph.nodes(data=True):
                if act_name.lower() in str(data.get('name', '')).lower():
                    best_match = node_id
                    break
            
            if best_match:
                orig_dur = self.graph.nodes[best_match].get('duration', 0)
                new_dur = orig_dur * (1 + (qty_change_pct / 100.0)) if qty_change_pct != 0 else orig_dur + 5
                self.graph.nodes[best_match]['duration'] = new_dur
                applied_count += 1
                
        # 4. Revised CPM
        if applied_count > 0:
            self.cpm_calculated = False
            revised_results = self.calculate_cpm_full()
            revised_duration = max([v['ef'] for v in revised_results.values()]) if revised_results else 0
            return int(max(0, revised_duration - baseline_duration))
        
        return 0
