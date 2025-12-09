#!/usr/bin/env python3
"""
Create a standalone HTML viewer with embedded test results data
"""

import json
from datetime import datetime

def load_test_results(file_path):
    """Load test results from JSON file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data

def format_test_results_for_js(results):
    """Format test results data for JavaScript embedding"""
    formatted_results = []
    
    for result in results:
        question_data = result.get('question_data', {})
        api_response = result.get('api_response', {})
        evaluation = result.get('evaluation', {})
        
        # Determine status
        if not api_response.get('success', False):
            status = 'error'
        elif evaluation.get('contains_sorry', False):
            status = 'partial'
        elif evaluation.get('answered', False):
            status = 'success'
        else:
            status = 'failed'
        
        # Format coverage
        coverage = evaluation.get('keyword_coverage', 0)
        coverage_class = 'high' if coverage >= 0.7 else 'medium' if coverage >= 0.3 else 'low'
        
        # Extract article ID from source
        sources = api_response.get('sources', [])
        article_id = 'Unknown'
        if sources and len(sources) > 0:
            source = sources[0]
            if 'ID=' in source:
                article_id = source.split('ID=')[1].split('&')[0] if '&' in source.split('ID=')[1] else source.split('ID=')[1]
        
        formatted_result = {
            'question_number': result.get('question_number', 0),
            'question': question_data.get('question', ''),
            'answer': api_response.get('answer', 'No answer available'),
            'status': status,
            'coverage': coverage,
            'coverage_class': coverage_class,
            'response_time': evaluation.get('response_time', 0),
            'sources': sources,
            'article_id': article_id,
            'article_url': question_data.get('article_url', ''),
            'keywords_found': evaluation.get('keywords_found', []),
            'keywords_missing': evaluation.get('keywords_missing', []),
            'expected_keywords': question_data.get('expected_answer_contains', [])
        }
        formatted_results.append(formatted_result)
    
    return formatted_results

def create_standalone_html(test_results_file, output_file):
    """Create standalone HTML file with embedded data"""
    
    # Load test results
    data = load_test_results(test_results_file)
    results = data.get('results', [])
    test_info = data.get('test_info', {})
    
    # Format results for JavaScript
    formatted_results = format_test_results_for_js(results)
    
    # Calculate statistics
    total_questions = len(formatted_results)
    successful = len([r for r in formatted_results if r['status'] == 'success'])
    partial = len([r for r in formatted_results if r['status'] == 'partial'])
    failed = len([r for r in formatted_results if r['status'] == 'failed'])
    errors = len([r for r in formatted_results if r['status'] == 'error'])
    
    success_rate = (successful / total_questions * 100) if total_questions > 0 else 0
    avg_response_time = sum(r['response_time'] for r in formatted_results) / total_questions if total_questions > 0 else 0
    avg_coverage = sum(r['coverage'] for r in formatted_results) / total_questions if total_questions > 0 else 0
    
    # Create the HTML content
    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Random Sample Test Results - Interactive Viewer</title>
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
        
        .filter-group {{
            display: flex;
            gap: 10px;
            align-items: center;
        }}
        
        .filter-group select {{
            padding: 8px 12px;
            border: 2px solid #e9ecef;
            border-radius: 6px;
            background: white;
            font-size: 14px;
        }}
        
        .results-table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        .results-table th {{
            background: #f8f9fa;
            padding: 15px 10px;
            text-align: left;
            font-weight: 600;
            color: #2c3e50;
            border-bottom: 2px solid #e9ecef;
            font-size: 13px;
        }}
        
        .results-table td {{
            padding: 15px 10px;
            border-bottom: 1px solid #f1f3f4;
            vertical-align: top;
            font-size: 13px;
        }}
        
        .results-table tr:hover {{
            background: #f8f9fa;
        }}
        
        .question-cell {{
            max-width: 300px;
            word-wrap: break-word;
        }}
        
        .answer-cell {{
            max-width: 400px;
            word-wrap: break-word;
        }}
        
        .status-badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: bold;
            text-transform: uppercase;
        }}
        
        .status-success {{ background: #d4edda; color: #155724; }}
        .status-partial {{ background: #fff3cd; color: #856404; }}
        .status-failed {{ background: #f8d7da; color: #721c24; }}
        .status-error {{ background: #f5c6cb; color: #721c24; }}
        
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
        
        .row-number {{
            text-align: center;
            font-weight: bold;
            color: #6c757d;
            font-size: 12px;
        }}
        
        .response-time {{
            font-size: 11px;
            color: #6c757d;
        }}
        
        .article-info {{
            font-size: 11px;
            color: #6c757d;
            margin-top: 3px;
        }}
        
        .keywords-info {{
            font-size: 11px;
            margin-top: 5px;
        }}
        
        .keywords-found {{
            color: #28a745;
        }}
        
        .keywords-missing {{
            color: #dc3545;
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
            <h1>🎲 Random Sample Test Results</h1>
            <div class="subtitle">100 Questions from Generated TeamDynamix Evaluation Set</div>
            <div class="stats">
                <div class="stat">
                    <div class="stat-number">{total_questions}</div>
                    <div class="stat-label">Total Questions</div>
                </div>
                <div class="stat">
                    <div class="stat-number">{success_rate:.0f}%</div>
                    <div class="stat-label">Success Rate</div>
                </div>
                <div class="stat">
                    <div class="stat-number">{avg_response_time:.1f}s</div>
                    <div class="stat-label">Avg Response Time</div>
                </div>
                <div class="stat">
                    <div class="stat-number">{avg_coverage:.0f}%</div>
                    <div class="stat-label">Avg Keyword Coverage</div>
                </div>
            </div>
        </div>
        
        <div class="controls">
            <div class="search-box">
                <input type="text" id="searchInput" placeholder="🔍 Search questions, answers, or sources...">
            </div>
            <div class="filter-group">
                <select id="statusFilter">
                    <option value="">All Status</option>
                    <option value="success">Success ({successful})</option>
                    <option value="partial">Partial ({partial})</option>
                    <option value="failed">Failed ({failed})</option>
                    <option value="error">Error ({errors})</option>
                </select>
                <select id="coverageFilter">
                    <option value="">All Coverage</option>
                    <option value="high">High (≥70%)</option>
                    <option value="medium">Medium (30-69%)</option>
                    <option value="low">Low (<30%)</option>
                </select>
            </div>
        </div>
        
        <div style="overflow-x: auto;">
            <table class="results-table">
                <thead>
                    <tr>
                        <th style="width: 40px;">#</th>
                        <th style="width: 300px;">Question</th>
                        <th style="width: 400px;">Answer</th>
                        <th style="width: 80px;">Status</th>
                        <th style="width: 100px;">Coverage</th>
                        <th style="width: 80px;">Time</th>
                        <th style="width: 200px;">Sources</th>
                    </tr>
                </thead>
                <tbody id="resultsTableBody">
                    <!-- Results will be populated by JavaScript -->
                </tbody>
            </table>
        </div>
    </div>

    <script>
        // Embedded test results data
        const testResultsData = {json.dumps(formatted_results, indent=8)};

        let filteredResults = [...testResultsData];

        function renderResults(results) {{
            const tbody = document.getElementById('resultsTableBody');
            tbody.innerHTML = '';

            results.forEach(result => {{
                const row = document.createElement('tr');
                
                // Coverage percentage and class
                const coveragePercent = Math.round(result.coverage * 100);
                const coverageClass = `coverage-${{result.coverage_class}}`;
                
                // Sources HTML
                const sourcesHtml = result.sources.map(source => {{
                    if (source.includes('teamdynamix.com')) {{
                        return `<a href="${{source}}" target="_blank">Article ${{result.article_id}}</a>`;
                    }}
                    return `<a href="${{source}}" target="_blank">${{source}}</a>`;
                }}).join(', ');
                
                // Keywords info
                const keywordsFoundHtml = result.keywords_found.length > 0 ? 
                    `<div class="keywords-found">✓ Found: ${{result.keywords_found.join(', ')}}</div>` : '';
                const keywordsMissingHtml = result.keywords_missing.length > 0 ? 
                    `<div class="keywords-missing">✗ Missing: ${{result.keywords_missing.join(', ')}}</div>` : '';
                
                row.innerHTML = `
                    <td class="row-number">${{result.question_number}}</td>
                    <td class="question-cell">
                        ${{result.question}}
                        <div class="article-info">From Article ${{result.article_id}}</div>
                    </td>
                    <td class="answer-cell">
                        ${{result.answer}}
                        <div class="keywords-info">
                            ${{keywordsFoundHtml}}
                            ${{keywordsMissingHtml}}
                        </div>
                    </td>
                    <td>
                        <span class="status-badge status-${{result.status}}">${{result.status}}</span>
                    </td>
                    <td>
                        <span class="keyword-coverage ${{coverageClass}}">${{coveragePercent}}%</span>
                    </td>
                    <td class="response-time">${{result.response_time.toFixed(2)}}s</td>
                    <td class="sources">${{sourcesHtml}}</td>
                `;
                
                tbody.appendChild(row);
            }});
        }}

        function filterResults() {{
            const searchTerm = document.getElementById('searchInput').value.toLowerCase();
            const statusFilter = document.getElementById('statusFilter').value;
            const coverageFilter = document.getElementById('coverageFilter').value;

            filteredResults = testResultsData.filter(result => {{
                // Search filter
                const matchesSearch = !searchTerm || 
                    result.question.toLowerCase().includes(searchTerm) ||
                    result.answer.toLowerCase().includes(searchTerm) ||
                    result.sources.some(source => source.toLowerCase().includes(searchTerm));

                // Status filter
                const matchesStatus = !statusFilter || result.status === statusFilter;

                // Coverage filter
                let matchesCoverage = true;
                if (coverageFilter === 'high') {{
                    matchesCoverage = result.coverage >= 0.7;
                }} else if (coverageFilter === 'medium') {{
                    matchesCoverage = result.coverage >= 0.3 && result.coverage < 0.7;
                }} else if (coverageFilter === 'low') {{
                    matchesCoverage = result.coverage < 0.3;
                }}

                return matchesSearch && matchesStatus && matchesCoverage;
            }});

            renderResults(filteredResults);
        }}

        // Event listeners
        document.getElementById('searchInput').addEventListener('input', filterResults);
        document.getElementById('statusFilter').addEventListener('change', filterResults);
        document.getElementById('coverageFilter').addEventListener('change', filterResults);

        // Initial render
        renderResults(testResultsData);
    </script>
</body>
</html>'''

    # Write the HTML file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ Standalone HTML viewer created: {output_file}")
    print(f"📊 Statistics:")
    print(f"   Total Questions: {total_questions}")
    print(f"   Success: {successful} ({success_rate:.1f}%)")
    print(f"   Partial: {partial}")
    print(f"   Failed: {failed}")
    print(f"   Errors: {errors}")
    print(f"   Avg Response Time: {avg_response_time:.2f}s")
    print(f"   Avg Coverage: {avg_coverage:.1f}%")

if __name__ == "__main__":
    test_results_file = "/home/exouser/AI-Agent-Askus/evaluation/test_results_20251205_035323.json"
    output_file = "/home/exouser/AI-Agent-Askus/evaluation/Random_Sample_Test_Results_Standalone.html"
    
    create_standalone_html(test_results_file, output_file)
