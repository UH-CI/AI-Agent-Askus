#!/usr/bin/env python3
"""
Generate a standalone HTML viewer for V3 evaluation results
"""

import json
import html
from datetime import datetime

def generate_html_viewer(json_file_path, output_html_path):
    """Generate a standalone HTML file with embedded evaluation data"""
    
    # Load the JSON data
    with open(json_file_path, 'r') as f:
        data = json.load(f)
    
    # Extract all questions and answers
    questions_data = []
    
    for article in data.get('articles', []):
        for question_result in article.get('question_results', []):
            api_response = question_result.get('api_response', {})
            evaluation = question_result.get('evaluation', {})
            
            # Determine if this is a "sorry" response
            is_sorry = evaluation.get('contains_sorry', False) or not api_response.get('success', False)
            
            question_data = {
                'question': question_result.get('question', ''),
                'answer': api_response.get('answer', 'No response available'),
                'success': api_response.get('success', False),
                'response_time': evaluation.get('response_time', 0),
                'source_count': evaluation.get('source_count', 0),
                'keyword_coverage': evaluation.get('keyword_coverage', 0),
                'is_sorry': is_sorry,
                'sources': api_response.get('sources', [])
            }
            questions_data.append(question_data)
    
    # Sort: answered questions first, sorry responses at the bottom
    questions_data.sort(key=lambda x: (x['is_sorry'], -x['keyword_coverage']))
    
    # Generate the HTML
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Agent Evaluation Results V3 - Interactive Viewer</title>
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
            font-size: 2em;
            font-weight: bold;
            color: #3498db;
        }}
        
        .stat-label {{
            font-size: 0.9em;
            opacity: 0.8;
        }}
        
        .controls {{
            padding: 20px 30px;
            background: #f8f9fa;
            border-bottom: 1px solid #e9ecef;
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
            padding: 12px 16px;
            border: 2px solid #e9ecef;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s;
        }}
        
        .search-box input:focus {{
            outline: none;
            border-color: #3498db;
        }}
        
        .export-btn {{
            background: #27ae60;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            transition: background 0.3s;
        }}
        
        .export-btn:hover {{
            background: #219a52;
        }}
        
        .table-container {{
            overflow-x: auto;
            max-height: 70vh;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }}
        
        th {{
            background: #34495e;
            color: white;
            padding: 15px 12px;
            text-align: left;
            font-weight: 600;
            position: sticky;
            top: 0;
            z-index: 10;
        }}
        
        td {{
            padding: 12px;
            border-bottom: 1px solid #e9ecef;
            vertical-align: top;
        }}
        
        tr:hover {{
            background: #f8f9fa;
        }}
        
        .question-cell {{
            max-width: 300px;
            font-weight: 600;
            color: #2c3e50;
        }}
        
        .answer-cell {{
            max-width: 400px;
            line-height: 1.5;
        }}
        
        .sorry-row {{
            background: #fff5f5;
        }}
        
        .sorry-row:hover {{
            background: #fed7d7;
        }}
        
        .success-indicator {{
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }}
        
        .success-true {{
            background: #27ae60;
        }}
        
        .success-false {{
            background: #e74c3c;
        }}
        
        .score-input {{
            width: 60px;
            padding: 6px;
            border: 2px solid #e9ecef;
            border-radius: 4px;
            text-align: center;
            font-size: 14px;
        }}
        
        .score-input:focus {{
            outline: none;
            border-color: #3498db;
        }}
        
        .metrics {{
            font-size: 12px;
            color: #666;
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
        
        .section-header {{
            background: #e9ecef;
            padding: 15px 20px;
            font-weight: bold;
            color: #495057;
            border-bottom: 2px solid #dee2e6;
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
            <h1>🤖 AI Agent Evaluation Results</h1>
            <div class="subtitle">Version 3 - Interactive Analysis Dashboard</div>
            <div class="subtitle">Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</div>
            
            <div class="stats">
                <div class="stat">
                    <div class="stat-number">{len(questions_data)}</div>
                    <div class="stat-label">Total Questions</div>
                </div>
                <div class="stat">
                    <div class="stat-number">{len([q for q in questions_data if not q['is_sorry']])}</div>
                    <div class="stat-label">Answered</div>
                </div>
                <div class="stat">
                    <div class="stat-number">{len([q for q in questions_data if q['is_sorry']])}</div>
                    <div class="stat-label">No Answer</div>
                </div>
                <div class="stat">
                    <div class="stat-number">{(len([q for q in questions_data if not q['is_sorry']]) / len(questions_data) * 100):.1f}%</div>
                    <div class="stat-label">Success Rate</div>
                </div>
            </div>
        </div>
        
        <div class="controls">
            <div class="search-box">
                <input type="text" id="searchInput" placeholder="🔍 Search questions or answers..." onkeyup="filterTable()">
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
                        <th style="width: 100px;">Metrics</th>
                        <th style="width: 80px;">Your Score</th>
                    </tr>
                </thead>
                <tbody>"""
    
    # Add section for answered questions
    answered_questions = [q for q in questions_data if not q['is_sorry']]
    sorry_questions = [q for q in questions_data if q['is_sorry']]
    
    if answered_questions:
        html_content += """
                    <tr class="section-header">
                        <td colspan="5">✅ Questions with Answers ({} items)</td>
                    </tr>""".format(len(answered_questions))
        
        for i, q in enumerate(answered_questions):
            coverage_class = 'coverage-high' if q['keyword_coverage'] > 0.6 else 'coverage-medium' if q['keyword_coverage'] > 0.2 else 'coverage-low'
            
            sources_html = ""
            if q['sources']:
                sources_html = "<div class='sources'>Sources: " + ", ".join([f"<a href='{src}' target='_blank'>{src.split('/')[-1]}</a>" for src in q['sources'][:3]]) + "</div>"
            
            html_content += f"""
                    <tr>
                        <td>
                            <span class="success-indicator success-{str(q['success']).lower()}"></span>
                        </td>
                        <td class="question-cell">{html.escape(q['question'])}</td>
                        <td class="answer-cell">
                            {html.escape(q['answer'])}
                            {sources_html}
                        </td>
                        <td>
                            <div class="metrics">
                                <div>⏱️ {q['response_time']:.1f}s</div>
                                <div>📚 {q['source_count']} sources</div>
                                <div><span class="keyword-coverage {coverage_class}">{q['keyword_coverage']:.0%} match</span></div>
                            </div>
                        </td>
                        <td>
                            <input type="number" class="score-input" min="0" max="10" placeholder="0-10" data-row="{i}">
                        </td>
                    </tr>"""
    
    # Add section for sorry responses
    if sorry_questions:
        html_content += """
                    <tr class="section-header">
                        <td colspan="5">❌ Questions Without Answers ({} items)</td>
                    </tr>""".format(len(sorry_questions))
        
        for i, q in enumerate(sorry_questions, len(answered_questions)):
            html_content += f"""
                    <tr class="sorry-row">
                        <td>
                            <span class="success-indicator success-false"></span>
                        </td>
                        <td class="question-cell">{html.escape(q['question'])}</td>
                        <td class="answer-cell">{html.escape(q['answer'])}</td>
                        <td>
                            <div class="metrics">
                                <div>⏱️ {q['response_time']:.1f}s</div>
                                <div>📚 {q['source_count']} sources</div>
                                <div><span class="keyword-coverage coverage-low">No answer</span></div>
                            </div>
                        </td>
                        <td>
                            <input type="number" class="score-input" min="0" max="10" placeholder="0-10" data-row="{i}">
                        </td>
                    </tr>"""
    
    # Close the HTML
    html_content += f"""
                </tbody>
            </table>
        </div>
    </div>

    <script>
        // Store the original data for filtering and export
        const evaluationData = {json.dumps(questions_data, indent=2)};
        
        function filterTable() {{
            const input = document.getElementById('searchInput');
            const filter = input.value.toLowerCase();
            const table = document.getElementById('evaluationTable');
            const rows = table.getElementsByTagName('tr');
            
            for (let i = 2; i < rows.length; i++) {{ // Skip header and section headers
                const row = rows[i];
                if (row.classList.contains('section-header')) continue;
                
                const question = row.cells[1].textContent.toLowerCase();
                const answer = row.cells[2].textContent.toLowerCase();
                
                if (question.includes(filter) || answer.includes(filter)) {{
                    row.style.display = '';
                }} else {{
                    row.style.display = 'none';
                }}
            }}
        }}
        
        function exportToCSV() {{
            const scores = [];
            const scoreInputs = document.querySelectorAll('.score-input');
            
            scoreInputs.forEach((input, index) => {{
                scores[index] = input.value || '';
            }});
            
            let csv = 'Question,Answer,Success,Response Time (s),Source Count,Keyword Coverage,User Score\\n';
            
            evaluationData.forEach((item, index) => {{
                const question = '"' + item.question.replace(/"/g, '""') + '"';
                const answer = '"' + item.answer.replace(/"/g, '""') + '"';
                const success = item.success;
                const responseTime = item.response_time.toFixed(2);
                const sourceCount = item.source_count;
                const keywordCoverage = (item.keyword_coverage * 100).toFixed(1) + '%';
                const userScore = scores[index] || '';
                
                csv += `${{question}},${{answer}},${{success}},${{responseTime}},${{sourceCount}},${{keywordCoverage}},${{userScore}}\\n`;
            }});
            
            const blob = new Blob([csv], {{ type: 'text/csv' }});
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'ai_evaluation_results_v3_' + new Date().toISOString().slice(0,10) + '.csv';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        }}
        
        // Auto-save scores to localStorage
        document.addEventListener('input', function(e) {{
            if (e.target.classList.contains('score-input')) {{
                const scores = [];
                document.querySelectorAll('.score-input').forEach((input, index) => {{
                    scores[index] = input.value;
                }});
                localStorage.setItem('ai_evaluation_scores_v3', JSON.stringify(scores));
            }}
        }});
        
        // Load saved scores
        window.addEventListener('load', function() {{
            const savedScores = localStorage.getItem('ai_evaluation_scores_v3');
            if (savedScores) {{
                const scores = JSON.parse(savedScores);
                document.querySelectorAll('.score-input').forEach((input, index) => {{
                    if (scores[index]) {{
                        input.value = scores[index];
                    }}
                }});
            }}
        }});
    </script>
</body>
</html>"""
    
    # Write the HTML file
    with open(output_html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ HTML viewer generated: {output_html_path}")
    print(f"📊 Total questions processed: {len(questions_data)}")
    print(f"✅ Answered questions: {len(answered_questions)}")
    print(f"❌ Sorry responses: {len(sorry_questions)}")

if __name__ == "__main__":
    generate_html_viewer(
        'evaluation_results_V3_20251203_215559.json',
        'AI_Evaluation_V3_Interactive_Viewer.html'
    )
