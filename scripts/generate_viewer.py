#!/usr/bin/env python3
"""
Generate index.html viewer from startlist_matrix.csv
"""

import csv
from pathlib import Path

MATRIX_FILE = Path("output/startlist_matrix.csv")
OUTPUT_HTML = Path("output/index.html")


def read_matrix():
    """Read the matrix CSV and return headers + rows."""
    with open(MATRIX_FILE, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        headers = reader.fieldnames
    return headers, rows


def generate_html(headers, rows):
    """Generate the interactive HTML viewer."""
    
    # Extract race names (all columns except rider_name and races_count)
    race_names = [h for h in headers if h not in ['rider_name', 'races_count']]
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cycling Startlists 2026 - Matrix Viewer</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            background: #f5f5f5;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            padding: 30px;
        }}
        
        header {{
            margin-bottom: 30px;
        }}
        
        h1 {{
            color: #333;
            margin-bottom: 10px;
        }}
        
        .subtitle {{
            color: #666;
            font-size: 16px;
        }}
        
        .stats {{
            display: flex;
            gap: 20px;
            margin: 20px 0;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 6px;
        }}
        
        .stat {{
            display: flex;
            flex-direction: column;
        }}
        
        .stat-label {{
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .stat-value {{
            font-size: 24px;
            font-weight: bold;
            color: #333;
        }}
        
        .controls {{
            margin-bottom: 20px;
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            align-items: center;
        }}
        
        .search-box {{
            flex: 1;
            min-width: 250px;
            padding: 10px 15px;
            font-size: 16px;
            border: 2px solid #ddd;
            border-radius: 6px;
            transition: border-color 0.2s;
        }}
        
        .search-box:focus {{
            outline: none;
            border-color: #4CAF50;
        }}
        
        .download-links {{
            display: flex;
            gap: 10px;
        }}
        
        .download-btn {{
            padding: 10px 20px;
            background: #4CAF50;
            color: white;
            text-decoration: none;
            border-radius: 6px;
            font-size: 14px;
            transition: background 0.2s;
        }}
        
        .download-btn:hover {{
            background: #45a049;
        }}
        
        .table-wrapper {{
            overflow-x: auto;
            border: 1px solid #ddd;
            border-radius: 6px;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }}
        
        thead {{
            background: #333;
            color: white;
            position: sticky;
            top: 0;
            z-index: 10;
        }}
        
        th {{
            padding: 12px 8px;
            text-align: left;
            font-weight: 600;
            white-space: nowrap;
            border-right: 1px solid #555;
        }}
        
        th:last-child {{
            border-right: none;
        }}
        
        .race-header {{
            writing-mode: vertical-rl;
            transform: rotate(180deg);
            padding: 8px 12px;
            min-height: 150px;
            text-align: left;
        }}
        
        tbody tr {{
            border-bottom: 1px solid #eee;
            transition: background 0.1s;
        }}
        
        tbody tr:hover {{
            background: #f8f9fa;
        }}
        
        tbody tr.hidden {{
            display: none;
        }}
        
        td {{
            padding: 10px 8px;
            border-right: 1px solid #eee;
        }}
        
        td:last-child {{
            border-right: none;
        }}
        
        .rider-name {{
            font-weight: 500;
            color: #333;
            min-width: 200px;
            position: sticky;
            left: 0;
            background: white;
            z-index: 5;
        }}
        
        tbody tr:hover .rider-name {{
            background: #f8f9fa;
        }}
        
        .presence {{
            text-align: center;
            color: #4CAF50;
            font-weight: bold;
        }}
        
        .races-count {{
            font-weight: 600;
            color: #333;
            text-align: center;
        }}
        
        .no-results {{
            text-align: center;
            padding: 40px;
            color: #999;
            font-style: italic;
        }}
        
        footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            color: #666;
            font-size: 14px;
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🚴 Cycling Startlists 2026</h1>
            <p class="subtitle">Spring Classics — Men's Races</p>
            
            <div class="stats">
                <div class="stat">
                    <span class="stat-label">Total Riders</span>
                    <span class="stat-value" id="totalRiders">{len(rows)}</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Races Tracked</span>
                    <span class="stat-value">{len(race_names)}</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Visible Riders</span>
                    <span class="stat-value" id="visibleRiders">{len(rows)}</span>
                </div>
            </div>
        </header>
        
        <div class="controls">
            <input 
                type="text" 
                class="search-box" 
                id="searchBox" 
                placeholder="Search by rider name..."
            >
            
            <div class="download-links">
                <a href="startlist_matrix.csv" class="download-btn" download>
                    ⬇ Matrix CSV
                </a>
                <a href="startlist_changes.csv" class="download-btn" download>
                    ⬇ Changes Log
                </a>
            </div>
        </div>
        
        <div class="table-wrapper">
            <table id="dataTable">
                <thead>
                    <tr>
                        <th>Rider</th>
"""
    
    # Add race column headers
    for race in race_names:
        html += f'                        <th class="race-header">{race}</th>\n'
    
    html += """                        <th>Races</th>
                    </tr>
                </thead>
                <tbody id="tableBody">
"""
    
    # Add data rows
    for row in rows:
        rider_name = row['rider_name']
        races_count = row['races_count']
        
        html += f'                    <tr>\n'
        html += f'                        <td class="rider-name">{rider_name}</td>\n'
        
        for race in race_names:
            presence = row.get(race, '')
            html += f'                        <td class="presence">{presence}</td>\n'
        
        html += f'                        <td class="races-count">{races_count}</td>\n'
        html += f'                    </tr>\n'
    
    html += """                </tbody>
            </table>
        </div>
        
        <footer>
            <p>Data from <a href="https://www.procyclingstats.com" target="_blank">ProCyclingStats</a></p>
            <p>Updates every 6 hours via GitHub Actions</p>
        </footer>
    </div>

    <script>
        // Search functionality
        const searchBox = document.getElementById('searchBox');
        const tableBody = document.getElementById('tableBody');
        const visibleRidersCount = document.getElementById('visibleRiders');
        const totalRiders = document.getElementById('totalRiders').textContent;
        
        searchBox.addEventListener('input', (e) => {
            const searchTerm = e.target.value.toLowerCase();
            const rows = tableBody.querySelectorAll('tr');
            let visibleCount = 0;
            
            rows.forEach(row => {
                const riderName = row.querySelector('.rider-name').textContent.toLowerCase();
                
                if (riderName.includes(searchTerm)) {
                    row.classList.remove('hidden');
                    visibleCount++;
                } else {
                    row.classList.add('hidden');
                }
            });
            
            visibleRidersCount.textContent = visibleCount;
        });
    </script>
</body>
</html>
"""
    
    return html


def main():
    print("Reading matrix CSV...")
    headers, rows = read_matrix()
    
    print("Generating HTML viewer...")
    html = generate_html(headers, rows)
    
    with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ Generated: {OUTPUT_HTML}")


if __name__ == "__main__":
    main()
