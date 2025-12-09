#!/usr/bin/env python3
"""
Create Standalone V4 Interactive Viewer
Embeds the V4 JSON data directly into the HTML file
"""

import json

def create_standalone_viewer():
    # Read the V4 evaluation results
    with open('/home/exouser/AI-Agent-Askus/evaluation/evaluation_results_V4_20251204_021730.json', 'r') as f:
        v4_data = json.load(f)
    
    # Convert V4 data to the format expected by the viewer
    evaluation_data = []
    
    if 'articles' in v4_data:
        for article in v4_data['articles']:
            if 'question_results' in article:
                for result in article['question_results']:
                    evaluation_data.append({
                        "question": result.get('question', ''),
                        "answer": result.get('api_response', {}).get('answer', 'No answer'),
                        "success": result.get('api_response', {}).get('success', False),
                        "response_time": result.get('evaluation', {}).get('response_time', 0),
                        "keyword_coverage": result.get('evaluation', {}).get('keyword_coverage', 0),
                        "keywords_found": result.get('evaluation', {}).get('keywords_found', []),
                        "keywords_missing": result.get('evaluation', {}).get('keywords_missing', []),
                        "sources": result.get('api_response', {}).get('sources', []),
                        "source_count": result.get('evaluation', {}).get('source_count', 0),
                        "answer_length": result.get('evaluation', {}).get('answer_length', 0),
                        "contains_sorry": result.get('evaluation', {}).get('contains_sorry', False),
                        "answered": result.get('evaluation', {}).get('answered', False),
                        "expected_keywords": result.get('expected_answer_contains', [])
                    })
    
    # Calculate stats
    total_questions = len(evaluation_data)
    answered_count = len([item for item in evaluation_data if item['answered'] and not item['contains_sorry']])
    sorry_count = len([item for item in evaluation_data if item['contains_sorry'] or not item['answered']])
    success_rate = (answered_count / total_questions * 100) if total_questions > 0 else 0
    
    # Create the standalone HTML
    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Agent Evaluation Results V4 - Interactive Viewer</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            font-weight: 300;
        }}
        
        .header .subtitle {{
            font-size: 1.1em;
            opacity: 0.9;
            margin-bottom: 20px;
        }}
        
        .stats {{
            display: flex;
            justify-content: center;
            gap: 30px;
            margin-top: 20px;
        }}
        
        .stat {{
            text-align: center;
        }}
        
        .stat-number {{
            font-size: 2.5em;
            font-weight: bold;
            color: #3498db;
        }}
        
        .stat-label {{
            font-size: 0.9em;
            opacity: 0.8;
            margin-top: 5px;
        }}
        
        .controls {{
            padding: 20px;
            background: #f8f9fa;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 15px;
        }}
        
        .search-box {{
            flex: 1;
            min-width: 300px;
        }}
        
        .search-box input {{
            width: 100%;
            padding: 12px 15px;
            border: 2px solid #e9ecef;
            border-radius: 8px;
            font-size: 14px;
            transition: border-color 0.3s;
        }}
        
        .search-box input:focus {{
            outline: none;
            border-color: #3498db;
        }}
        
        .filter-buttons {{
            display: flex;
            gap: 10px;
        }}
        
        .filter-btn {{
            padding: 8px 16px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 12px;
            font-weight: bold;
            transition: all 0.3s;
        }}
        
        .filter-btn.active {{
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }}
        
        .filter-all {{ background: #6c757d; color: white; }}
        .filter-answered {{ background: #28a745; color: white; }}
        .filter-sorry {{ background: #dc3545; color: white; }}
        
        .export-btn {{
            background: #17a2b8;
            color: white;
            border: none;
            padding: 12px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: bold;
            transition: background 0.3s;
        }}
        
        .export-btn:hover {{
            background: #138496;
        }}
        
        .table-container {{
            overflow-x: auto;
            max-height: 70vh;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #dee2e6;
            vertical-align: top;
        }}
        
        th {{
            background: #f8f9fa;
            font-weight: bold;
            color: #495057;
            position: sticky;
            top: 0;
            z-index: 10;
        }}
        
        tr:hover {{
            background: #f8f9fa;
        }}
        
        .status-icon {{
            font-size: 20px;
            text-align: center;
        }}
        
        .status-answered {{ color: #28a745; }}
        .status-sorry {{ color: #dc3545; }}
        
        .question-cell {{
            font-weight: 500;
            color: #2c3e50;
            max-width: 300px;
            word-wrap: break-word;
        }}
        
        .answer-cell {{
            max-width: 400px;
            word-wrap: break-word;
            font-size: 13px;
            line-height: 1.4;
        }}
        
        .answer-preview {{
            max-height: 100px;
            overflow: hidden;
            position: relative;
        }}
        
        .answer-full {{
            display: none;
        }}
        
        .expand-btn {{
            background: #007bff;
            color: white;
            border: none;
            padding: 4px 8px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 11px;
            margin-top: 5px;
        }}
        
        .metrics {{
            font-size: 12px;
        }}
        
        .metric-row {{
            margin-bottom: 3px;
        }}
        
        .sources {{
            font-size: 11px;
            color: #888;
            margin-top: 5px;
        }}
        
        .sources a {{
            color: #3498db;
            text-decoration: none;
        }}
        
        .sources a:hover {{
            text-decoration: underline;
        }}
        
        .keyword-coverage {{
            display: inline-block;
            padding: 2px 6px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: bold;
        }}
        
        .coverage-high {{ background: #d4edda; color: #155724; }}
        .coverage-medium {{ background: #fff3cd; color: #856404; }}
        .coverage-low {{ background: #f8d7da; color: #721c24; }}
        
        .improvement-badge {{
            display: inline-block;
            padding: 2px 6px;
            border-radius: 12px;
            font-size: 10px;
            font-weight: bold;
            background: #28a745;
            color: white;
            margin-left: 5px;
        }}
        
        @media (max-width: 768px) {{
            .controls {{
                flex-direction: column;
                align-items: stretch;
            }}
            
            .search-box {{
                min-width: auto;
            }}
            
            .stats {{
                flex-direction: column;
                gap: 15px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 AI Agent Evaluation Results</h1>
            <div class="subtitle">Version 4 - Question-Based RAG System</div>
            <div class="subtitle">Generated on December 04, 2025 at 2:17 AM</div>
            
            <div class="stats">
                <div class="stat">
                    <div class="stat-number">{total_questions}</div>
                    <div class="stat-label">Total Questions</div>
                </div>
                <div class="stat">
                    <div class="stat-number">{answered_count}</div>
                    <div class="stat-label">Answered</div>
                </div>
                <div class="stat">
                    <div class="stat-number">{sorry_count}</div>
                    <div class="stat-label">Sorry Responses</div>
                </div>
                <div class="stat">
                    <div class="stat-number">{success_rate:.1f}%</div>
                    <div class="stat-label">Success Rate</div>
                </div>
            </div>
        </div>
        
        <div class="controls">
            <div class="search-box">
                <input type="text" id="searchInput" placeholder="🔍 Search questions or answers..." onkeyup="filterTable()">
            </div>
            <div class="filter-buttons">
                <button class="filter-btn filter-all active" onclick="filterByStatus('all')">All</button>
                <button class="filter-btn filter-answered" onclick="filterByStatus('answered')">Answered</button>
                <button class="filter-btn filter-sorry" onclick="filterByStatus('sorry')">Sorry</button>
            </div>
            <button class="export-btn" onclick="exportToCSV()">📊 Export to CSV</button>
        </div>
        
        <div class="table-container">
            <table id="evaluationTable">
                <thead>
                    <tr>
                        <th style="width: 50px;">Status</th>
                        <th style="width: 300px;">Question</th>
                        <th style="width: 400px;">AI Answer</th>
                        <th style="width: 120px;">Metrics</th>
                        <th style="width: 80px;">Sources</th>
                    </tr>
                </thead>
                <tbody id="tableBody">
                    <!-- Data will be populated by JavaScript -->
                </tbody>
            </table>
        </div>
    </div>

    <script>
        // Embedded evaluation data
        const evaluationData = {json.dumps(evaluation_data, indent=2)};
        let currentFilter = 'all';

        // Initialize the page
        document.addEventListener('DOMContentLoaded', function() {{
            populateTable();
        }});

        function populateTable() {{
            const tbody = document.getElementById('tableBody');
            tbody.innerHTML = '';
            
            let filteredData = evaluationData;
            
            // Apply status filter
            if (currentFilter === 'answered') {{
                filteredData = evaluationData.filter(item => item.answered && !item.contains_sorry);
            }} else if (currentFilter === 'sorry') {{
                filteredData = evaluationData.filter(item => item.contains_sorry || !item.answered);
            }}
            
            // Apply search filter
            const searchTerm = document.getElementById('searchInput').value.toLowerCase();
            if (searchTerm) {{
                filteredData = filteredData.filter(item => 
                    item.question.toLowerCase().includes(searchTerm) ||
                    item.answer.toLowerCase().includes(searchTerm)
                );
            }}
            
            filteredData.forEach((item, index) => {{
                const row = document.createElement('tr');
                
                // Status
                const isAnswered = item.answered && !item.contains_sorry;
                const statusIcon = isAnswered ? '✅' : '❌';
                const statusClass = isAnswered ? 'status-answered' : 'status-sorry';
                
                // Coverage badge
                let coverageBadge = '';
                if (item.keyword_coverage > 0.7) {{
                    coverageBadge = '<span class="keyword-coverage coverage-high">' + Math.round(item.keyword_coverage * 100) + '%</span>';
                }} else if (item.keyword_coverage > 0.3) {{
                    coverageBadge = '<span class="keyword-coverage coverage-medium">' + Math.round(item.keyword_coverage * 100) + '%</span>';
                }} else {{
                    coverageBadge = '<span class="keyword-coverage coverage-low">' + Math.round(item.keyword_coverage * 100) + '%</span>';
                }}
                
                // Answer preview/full
                const answerId = `answer-${{index}}`;
                const answerPreview = item.answer.length > 200 ? item.answer.substring(0, 200) + '...' : item.answer;
                const needsExpand = item.answer.length > 200;
                
                // Sources
                let sourcesHtml = '';
                if (item.sources && item.sources.length > 0) {{
                    sourcesHtml = item.sources.map(source => {{
                        const shortSource = source.length > 50 ? source.substring(0, 50) + '...' : source;
                        return `<a href="${{source}}" target="_blank">${{shortSource}}</a>`;
                    }}).join('<br>');
                }}
                
                row.innerHTML = `
                    <td class="${{statusClass}}">${{statusIcon}}</td>
                    <td class="question-cell">${{item.question}}</td>
                    <td class="answer-cell">
                        <div class="answer-preview" id="${{answerId}}-preview">${{answerPreview}}</div>
                        <div class="answer-full" id="${{answerId}}-full">${{item.answer}}</div>
                        ${{needsExpand ? `<button class="expand-btn" onclick="toggleAnswer('${{answerId}}')">Show More</button>` : ''}}
                    </td>
                    <td class="metrics">
                        <div class="metric-row">Coverage: ${{coverageBadge}}</div>
                        <div class="metric-row">Time: ${{item.response_time.toFixed(2)}}s</div>
                        <div class="metric-row">Length: ${{item.answer_length}}</div>
                        <div class="metric-row">Sources: ${{item.source_count}}</div>
                    </td>
                    <td class="sources">${{sourcesHtml}}</td>
                `;
                
                tbody.appendChild(row);
            }});
        }}

        function filterTable() {{
            populateTable();
        }}

        function filterByStatus(status) {{
            currentFilter = status;
            
            // Update button states
            document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
            document.querySelector(`.filter-${{status}}`).classList.add('active');
            
            populateTable();
        }}

        function toggleAnswer(answerId) {{
            const preview = document.getElementById(answerId + '-preview');
            const full = document.getElementById(answerId + '-full');
            const button = preview.parentNode.querySelector('.expand-btn');
            
            if (preview.style.display === 'none') {{
                preview.style.display = 'block';
                full.style.display = 'none';
                button.textContent = 'Show More';
            }} else {{
                preview.style.display = 'none';
                full.style.display = 'block';
                button.textContent = 'Show Less';
            }}
        }}

        function exportToCSV() {{
            const headers = ['Status', 'Question', 'Answer', 'Keyword Coverage', 'Response Time', 'Answer Length', 'Source Count', 'Sources'];
            const csvContent = [
                headers.join(','),
                ...evaluationData.map(item => [
                    item.answered && !item.contains_sorry ? 'Answered' : 'Sorry',
                    `"${{item.question.replace(/"/g, '""')}}"`,
                    `"${{item.answer.replace(/"/g, '""')}}"`,
                    Math.round(item.keyword_coverage * 100) + '%',
                    item.response_time.toFixed(2),
                    item.answer_length,
                    item.source_count,
                    `"${{item.sources.join('; ').replace(/"/g, '""')}}"`
                ].join(','))
            ].join('\\n');
            
            const blob = new Blob([csvContent], {{ type: 'text/csv' }});
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'ai_evaluation_results_v4.csv';
            a.click();
            window.URL.revokeObjectURL(url);
        }}
    </script>
</body>
</html>'''
    
    # Write the standalone HTML file
    output_file = '/home/exouser/AI-Agent-Askus/evaluation/AI_Evaluation_V4_Interactive_Viewer_Standalone.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ Created standalone V4 viewer: {output_file}")
    print(f"📊 Stats: {total_questions} questions, {answered_count} answered ({success_rate:.1f}% success rate)")
    print(f"🚀 The viewer is completely standalone - no external files needed!")

if __name__ == "__main__":
    create_standalone_viewer()
