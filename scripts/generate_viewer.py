<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Startlist Viewer</title>
    <style>
        table, th, td {
            border: 1px solid black;
            border-collapse: collapse;
        }
        th, td {
            padding: 10px;
            text-align: left;
        }
    </style>
</head>
<body>
    <h1>Startlist Viewer</h1>
    <input type="text" id="search" placeholder="Search by rider name...">
    <table id="startlistTable">
        <thead>
            <tr>
                <th>Rider Name</th>
                <th>Team</th>
                <th>Race</th>
                <th>Statistics</th>
            </tr>
        </thead>
        <tbody>
            <!-- Rows will be populated here by JavaScript -->
        </tbody>
    </table>
    <p id="statistics"></p>
    <a id="downloadCsv" href="#">Download CSV</a>

    <script>
        function loadCSV(callback) {
            fetch('startlist.csv')
                .then(response => response.text())
                .then(data => {
                    const rows = data.split('\n').map(row => row.split(','));
                    callback(rows);
                });
        }

        function renderTable(data) {
            const tableBody = document.getElementById('startlistTable').getElementsByTagName('tbody')[0];
            tableBody.innerHTML = '';
            let totalRiders = data.length - 1; // exclude header
            let raceStats = {};

            data.slice(1).forEach(row => {
                const newRow = tableBody.insertRow();
                row.forEach(cell => {
                    const newCell = newRow.insertCell();
                    newCell.textContent = cell;
                });
                // Update race statistics logic here
                raceStats[row[2]] = (raceStats[row[2]] || 0) + 1; // assuming Race is the third column
            });

            // Display statistics
            document.getElementById('statistics').textContent = `Total Riders: ${totalRiders}`;
            document.getElementById('downloadCsv').setAttribute('href', 'startlist.csv');

            // Search functionality
            document.getElementById('search').addEventListener('keyup', function() {
                const filter = this.value.toLowerCase();
                Array.from(tableBody.rows).forEach(row => {
                    const riderName = row.cells[0].textContent.toLowerCase();
                    row.style.display = riderName.includes(filter) ? '' : 'none';
                });
            });
        }

        loadCSV(renderTable);
    </script>
</body>
</html>
