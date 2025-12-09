#!/usr/bin/env python3
"""
Create a standalone HTML viewer matching the exact format of AI_Evaluation_V4_Interactive_Viewer_Standalone.html
"""

import json
from datetime import datetime

def load_test_results(file_path):
    """Load test results from JSON file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data

def format_test_results_for_original_format(results):
    """Format test results data to match the original evaluation format"""
    formatted_results = []
    
    for result in results:
        question_data = result.get('question_data', {})
        api_response = result.get('api_response', {})
        evaluation = result.get('evaluation', {})
        
        # Determine success status (not sorry response)
        success = api_response.get('success', False) and not evaluation.get('contains_sorry', False)
        
        # Calculate score based on keyword coverage and success
        coverage = evaluation.get('keyword_coverage', 0)
        if not success:
            score = 0  # Sorry responses get 0
        elif coverage >= 0.8:
            score = 5  # Excellent
        elif coverage >= 0.6:
            score = 4  # Good
        elif coverage >= 0.4:
            score = 3  # Okay
        elif coverage >= 0.2:
            score = 2  # Slightly answered
        elif coverage > 0:
            score = 1  # Minimum
        else:
            score = 0  # Wrong
        
        formatted_result = {
            'question': question_data.get('question', ''),
            'answer': api_response.get('answer', 'No answer available'),
            'success': success,
            'response_time': evaluation.get('response_time', 0),
            'keyword_coverage': coverage,
            'keywords_found': evaluation.get('keywords_found', []),
            'keywords_missing': evaluation.get('keywords_missing', []),
            'sources': api_response.get('sources', []),
            'score': score
        }
        formatted_results.append(formatted_result)
    
    return formatted_results

def read_original_html_template():
    """Read the original HTML file and extract the template structure"""
    with open('/home/exouser/AI-Agent-Askus/evaluation/AI_Evaluation_V4_Interactive_Viewer_Standalone.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split at the data section - find the start of the data array
    before_data = content.split('const evaluationData = [')[0] + 'const evaluationData = '
    
    # Find the end of the data array and get everything after it
    # Look for the closing ]; followed by JavaScript code
    data_end_pattern = '];'
    data_start_idx = content.find('const evaluationData = [')
    if data_start_idx != -1:
        # Find the matching ]; after the data array
        remaining_content = content[data_start_idx:]
        bracket_count = 0
        in_array = False
        end_idx = -1
        
        for i, char in enumerate(remaining_content):
            if char == '[':
                bracket_count += 1
                in_array = True
            elif char == ']' and in_array:
                bracket_count -= 1
                if bracket_count == 0:
                    # Found the end of the array, look for the semicolon
                    if i + 1 < len(remaining_content) and remaining_content[i + 1] == ';':
                        end_idx = data_start_idx + i + 2
                        break
        
        if end_idx != -1:
            after_data = content[end_idx:]
        else:
            # Fallback method
            after_data = content.split('];', 1)[1]
    else:
        after_data = content.split('];', 1)[1]
    
    return before_data, after_data

def create_matching_html(test_results_file, output_file):
    """Create HTML file matching the exact format of the original"""
    
    # Load test results
    data = load_test_results(test_results_file)
    results = data.get('results', [])
    test_info = data.get('test_info', {})
    
    # Format results for the original format
    formatted_results = format_test_results_for_original_format(results)
    
    # Calculate statistics
    total_questions = len(formatted_results)
    answered = len([r for r in formatted_results if r['success']])
    sorry_responses = len([r for r in formatted_results if not r['success']])
    success_rate = (answered / total_questions * 100) if total_questions > 0 else 0
    
    # Read original template
    before_data, after_data = read_original_html_template()
    
    # Update the header information
    updated_before = before_data.replace(
        '<h1>🚀 AI Agent Evaluation Results</h1>',
        '<h1>🎲 Random Sample Test Results</h1>'
    ).replace(
        '<div class="subtitle">Version 4 - Question-Based RAG System</div>',
        '<div class="subtitle">100 Questions from Generated TeamDynamix Evaluation Set</div>'
    ).replace(
        '<div class="subtitle">Generated on December 04, 2025 at 2:17 AM</div>',
        f'<div class="subtitle">Generated on {datetime.now().strftime("%B %d, %Y at %I:%M %p")}</div>'
    ).replace(
        '<div class="stat-number">222</div>',
        f'<div class="stat-number">{total_questions}</div>'
    ).replace(
        '<div class="stat-number">204</div>',
        f'<div class="stat-number">{answered}</div>'
    ).replace(
        '<div class="stat-number">18</div>',
        f'<div class="stat-number">{sorry_responses}</div>'
    ).replace(
        '<div class="stat-number">91.9%</div>',
        f'<div class="stat-number">{success_rate:.1f}%</div>'
    )
    
    # Create the complete HTML content
    html_content = updated_before + 'const evaluationData = ' + json.dumps(formatted_results, indent=2) + after_data
    
    # Write the HTML file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ Matching HTML viewer created: {output_file}")
    print(f"📊 Statistics:")
    print(f"   Total Questions: {total_questions}")
    print(f"   Answered: {answered}")
    print(f"   Sorry Responses: {sorry_responses}")
    print(f"   Success Rate: {success_rate:.1f}%")
    
    # Score distribution
    score_dist = {}
    for result in formatted_results:
        score = result['score']
        score_dist[score] = score_dist.get(score, 0) + 1
    
    print(f"   Score Distribution:")
    for score in sorted(score_dist.keys(), reverse=True):
        print(f"     Score {score}: {score_dist[score]} questions")

if __name__ == "__main__":
    test_results_file = "/home/exouser/AI-Agent-Askus/evaluation/test_results_20251205_035323.json"
    output_file = "/home/exouser/AI-Agent-Askus/evaluation/Random_Sample_Test_Results_Matching_Format.html"
    
    create_matching_html(test_results_file, output_file)
