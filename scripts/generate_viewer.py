#!/usr/bin/env python3
"""
Generate a static HTML viewer for the startlist matrix.
Includes search and filtering functionality with vanilla JS.
"""

import csv
from pathlib import Path

def load_matrix_csv(csv_path: str) -> tuple:
    """Load matrix CSV and return (headers, rows)."""
    headers = []
    rows = []
    
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        headers = next(reader)
        for row in reader:
            rows.append(row)
    
    return headers, rows

def escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;"))

def generate_html(headers: list, rows: list, output_path: str):
    """Generate static HTML viewer."""
    
    # Build race columns (all except first 2 and last)
    race_columns = headers[2:-1]
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cycling Startlists 2026</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: #f5f5f5;
            padding: 20px;
            color: #333;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            padding: 30px;
        }}
        
        h1 {{
            margin-bottom: 10px;
            color: #222;
        }}
        
        .subtitle {{
            color: #666;
            margin-bottom: 20px;
            font-size: 14px;
        }}
        
        .controls {{
            display: flex;
            gap: 20px;
            margin-bottom: 20px;
            flex-wrap: wrap;
            align-items: center;
        }}
        
        .search-box {{
            flex: 1;
            min-width: 200px;
        }}
        
        .search-box input {{
            width: 100%;
            padding: 10px 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }}
        
        .search-box input::placeholder {{
            color: #999;
        }}
        
        .stats {{
            color: #666;
            font-size: 14px;
            white-space: nowrap;
        }}
        
        .links {{
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
        }}
        
        .links a {{
            color: #0366d6;
            text-decoration: none;
            font-size: 14px;
        }}
        
        .links a:hover {{
            text-decoration: underline;
        }}
        
        .table-wrapper {{
            overflow-x: auto;
            border: 1px solid #e1e4e8;
            border-radius: 4px;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }}
        
        thead {{
            background: #f6f8fa;
            position: sticky;
            top: 0;
            z-index: 10;
        }}
        
        th {{
            padding: 12px 8px;
            text-align: left;
            font-weight: 600;
            border-bottom: 2px solid #e1e4e8;
            white-space: nowrap;
            max-width: 120px;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        
        th:first-child {{
            position: sticky;
            left: 0;
            background: #f6f8fa;
            z-index: 11;
            padding-left: 12px;
        }}
        
        th:nth-child(2) {{
            position: sticky;
            left: 200px;
            background: #f6f8fa;
            z-index: 11;
            display: none;
        }}
        
        td {{
            padding: 10px 8px;
            border-bottom: 1px solid #e1e4e8;
        }}
        
        td:first-child {{
            position: sticky;
            left: 0;
            background: white;
            z-index: 9;
            font-weight: 500;
            max-width: 200px;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        
        td:nth-child(2) {{
            display: none;
        }}
        
        .race-cell {{
            text-align: center;
            color: #0366d6;
            font-weight: 600;
        }}
        
        .races-count {{
            text-align: center;
            font-weight: 600;
            color: #666;
        }}
        
        tbody tr:hover {{
            background: #fafbfc;
        }}
        
        .hidden {{
            display: none;
        }}
        
        .info {{
            margin-top: 20px;
            padding: 15px;
            background: #f6f8fa;
            border-left: 4px solid #0366d6;
            border-radius: 4px;
            font-size: 13px;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚴 2026 Cycling Startlists Matrix</h1>
        <p class="subtitle">Spring Classics season — tracking rider presence across 19 races</p>
        
        <div class="controls">
            <div class="search-box">
                <input 
                    type="text" 
                    id="searchInput" 
                    placeholder="Search by rider name..."
                    autocomplete="off"
                >
            </div>
            <div class="stats">
                <span id="rowCount">-</span> riders · <span id="raceCount">{len(race_columns)}</span> races
            </div>
            <div class="links">
                <a href="startlist_matrix.csv" download>📥 Download CSV</a>
                <a href="startlist_changes.csv" download>📋 Changes Log</a>
                <a href="startlist_snapshot.json" download>📸 Snapshot</a>
            </div>
        </div>
        
        <div class="table-wrapper">
            <table id="riderTable">
                <thead>
                    <tr>
"""
    # Add table headers
    for header in headers:
        html += f'                        <th title="{escape_html(header)}">{escape_html(header)}</th>\n'
    
    html += """                    </tr>
                </thead>
                <tbody id="tableBody">
"""
    # Add table rows
    for row in rows:
        html += "                    <tr>\n"
        for i, cell in enumerate(row):
            cell_escaped = escape_html(cell)
            if i >= 2 and i < len(headers) - 1:
                # Race cell with X
                html += f'                        <td class="race-cell">{cell_escaped}</td>\n'
            elif i == len(headers) - 1:
                # races_count column
                html += f'                        <td class="races-count">{cell_escaped}</td>\n'
            else:
                html += f'                        <td>{cell_escaped}</td>\n'
        html += "                    </tr>\n"
    
    html += """                </tbody>
            </table>
        </div>
        
        <div class="info">
            <strong>ℹ️ About:</strong> This matrix updates every 6 hours via GitHub Actions, fetching the latest startlists from 
            <a href="https://www.procyclingstats.com" target="_blank">ProCyclingStats</a>. 
            See the <a href="../../#readme" target="_blank">README</a> for details. 
            Search is case-insensitive and searches rider names only.
        </div>
    </div>
    
    <script>
        // Load data from table
        const table = document.getElementById('riderTable');
        const tbody = document.getElementById('tableBody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        const searchInput = document.getElementById('searchInput');
        const rowCountSpan = document.getElementById('rowCount');
        
        function updateCount() {
            const visibleRows = rows.filter(r => !r.classList.contains('hidden'));
            rowCountSpan.textContent = visibleRows.length;
        }
        
        function filterTable() {
            const query = searchInput.value.toLowerCase();
            
            rows.forEach(row => {
                const cells = row.querySelectorAll('td');
                if (cells.length > 0) {
                    const riderName = cells[0].textContent.toLowerCase();
                    const matches = riderName.includes(query);
                    
                    if (query === '' || matches) {
                        row.classList.remove('hidden');
                    } else {
                        row.classList.add('hidden');
                    }
                }
            });
            
            updateCount();
        }
        
        searchInput.addEventListener('input', filterTable);
        searchInput.addEventListener('change', filterTable);
        
        // Initialize
        updateCount();
    </script>
</body>
</html>\n"""