import base64
import numpy as np
from bs4 import BeautifulSoup
import re
import html
import json

def clean_wikipedia_html(html_string):
    """Clean and extract text content from Wikipedia HTML."""
    soup = BeautifulSoup(html_string, 'html.parser')

    # Remove all non-visible or irrelevant tags
    for tag in soup(['script', 'style', 'head', 'meta', 'noscript', 'link']):
        tag.decompose()

    # Target only main article content
    content_div = soup.find('div', id='mw-content-text')
    if content_div:
        text = content_div.get_text(separator=' ')
    else:
        text = soup.get_text(separator=' ')

    # Unescape HTML entities (e.g., &nbsp;)
    text = html.unescape(text)

    # Replace all types of whitespace (including unicode ones) with single spaces
    text = re.sub(r'\s+', ' ', text)
    
    # Optional: remove common Wikipedia junk phrases
    junk_phrases = ['Jump to:', 'navigation', 'search', 'From Wikipedia, the free encyclopedia']
    for phrase in junk_phrases:
        text = text.replace(phrase, '')

    return text.strip()


class LongAnswerCandidate(object):
    """Representation of long answer candidate."""

    def __init__(self, contents, index, is_answer, contains_answer):
        self.contents = contents
        self.index = index
        self.is_answer = is_answer
        self.contains_answer = contains_answer
        if is_answer:
            self.style = 'is_answer'
        elif contains_answer:
            self.style = 'contains_answer'
        else:
            self.style = 'not_answer'


class Example(object):
    """Example representation."""

    def __init__(self, json_example):
        self.json_example = json_example

        # Whole example info.
        self.url = json_example['document_url']
        self.title = json_example.get('document_title', 'Wikipedia')
        self.example_id = base64.urlsafe_b64encode(
            str(self.json_example['example_id']).encode('utf-8'))
        self.document_html = self.json_example['document_html'].encode('utf-8')
        self.document_tokens = self.json_example['document_tokens']
        self.question_text = json_example['question_text']

        
        if len(json_example['annotations']) != 5:
            raise ValueError('Dev set json_examples should have five annotations.')
        self.has_long_answer = sum([
            annotation['long_answer']['start_byte'] >= 0
            for annotation in json_example['annotations']
        ]) >= 2
        self.has_short_answer = sum([
            bool(annotation['short_answers']) or
            annotation['yes_no_answer'] != 'NONE'
            for annotation in json_example['annotations']
        ]) >= 2

        self.long_answers = [
            a['long_answer']
            for a in json_example['annotations']
            if a['long_answer']['start_byte'] >= 0 and self.has_long_answer
        ]
        self.short_answers = [
            a['short_answers']
            for a in json_example['annotations']
            if a['short_answers'] and self.has_short_answer
        ]
        self.yes_no_answers = [
            a['yes_no_answer']
            for a in json_example['annotations']
            if a['yes_no_answer'] != 'NONE' and self.has_short_answer
        ]

        if self.has_long_answer:
            long_answer_bounds = [
                (la['start_byte'], la['end_byte']) for la in self.long_answers
            ]
            long_answer_counts = [
                long_answer_bounds.count(la) for la in long_answer_bounds
            ]
            long_answer = self.long_answers[np.argmax(long_answer_counts)]
            self.long_answer_text = self.render_long_answer(long_answer)
        else:
            self.long_answer_text = ''

        if self.has_short_answer:
            short_answers_ids = [[
                (s['start_byte'], s['end_byte']) for s in a
            ] for a in self.short_answers] + [a for a in self.yes_no_answers]
            short_answers_counts = [
                short_answers_ids.count(a) for a in short_answers_ids
            ]

            self.short_answers_texts = [
                ', '.join([
                    self.render_span(s['start_byte'], s['end_byte'])
                    for s in short_answer
                ])
                for short_answer in self.short_answers
            ]

            self.short_answers_texts += self.yes_no_answers
            self.short_answers_text = self.short_answers_texts[np.argmax(
                short_answers_counts)]
            self.short_answers_texts = set(self.short_answers_texts)

        else:
            self.short_answers_texts = []
            self.short_answers_text = ''

        self.candidates = self.get_candidates(
            self.json_example['long_answer_candidates'])

        self.candidates_with_answer = [
            i for i, c in enumerate(self.candidates) if c.contains_answer
        ]

    def render_long_answer(self, long_answer):
        """Wrap table rows and list items, and render the long answer.

        Args:
            long_answer: Long answer dictionary.

        Returns:
            String representation of the long answer span.
        """

        if long_answer['end_token'] - long_answer['start_token'] > 500:
            return 'Large long answer'

        html_tag = self.document_tokens[long_answer['end_token'] - 1]['token']
        if html_tag == '</Table>' and self.render_span(
                long_answer['start_byte'], long_answer['end_byte']).count('<TR>') > 30:
            return 'Large table long answer'

        elif html_tag == '</Tr>':
            return '<TABLE>{}</TABLE>'.format(
                self.render_span(long_answer['start_byte'], long_answer['end_byte']))

        elif html_tag in ['</Li>', '</Dd>', '</Dd>']:
            return '<Ul>{}</Ul>'.format(
                self.render_span(long_answer['start_byte'], long_answer['end_byte']))

        else:
            return self.render_span(long_answer['start_byte'],
                                  long_answer['end_byte'])

    def render_span(self, start, end):
        return self.document_html[start:end].decode()

    def get_candidates(self, json_candidates):
        """Returns a list of `LongAnswerCandidate` objects for top level candidates.

        Args:
            json_candidates: List of Json records representing candidates.

        Returns:
            List of `LongAnswerCandidate` objects.
        """
        candidates = []
        top_level_candidates = [c for c in json_candidates if c['top_level']]
        for candidate in top_level_candidates:
            tokenized_contents = ' '.join([
                t['token'] for t in self.json_example['document_tokens']
                [candidate['start_token']:candidate['end_token']]
            ])

            start = candidate['start_byte']
            end = candidate['end_byte']
            is_answer = self.has_long_answer and np.any(
                [(start == ans['start_byte']) and (end == ans['end_byte'])
                 for ans in self.long_answers])
            contains_answer = self.has_long_answer and np.any(
                [(start <= ans['start_byte']) and (end >= ans['end_byte'])
                 for ans in self.long_answers])

            candidates.append(
                LongAnswerCandidate(tokenized_contents, len(candidates), is_answer,
                                    contains_answer))

        return candidates


class QuestionAnswerer:
    """A class for answering questions based on Wikipedia data."""
    
    def __init__(self, json_data):
        """Initialize with JSON data containing document and question info.
        
        Args:
            json_data: A JSON object containing document and question information.
                       Expected to have keys like 'document_html', 'document_tokens',
                       'long_answer_candidates', etc.
        """
        self.json_data = json_data
        self.example = None
        
        # Only attempt to create an Example if the required keys are present
        required_keys = ['document_html', 'document_tokens', 'long_answer_candidates', 'example_id']
        if all(key in json_data for key in required_keys):
            try:
                # Handle the case where annotations might not be present or in the expected format
                if 'annotations' not in json_data:
                    # Create dummy annotations for non-annotated data
                    self.json_data['annotations'] = [
                        {
                            'long_answer': {'start_byte': -1, 'end_byte': -1, 'start_token': -1, 'end_token': -1},
                            'short_answers': [],
                            'yes_no_answer': 'NONE'
                        } for _ in range(5)  # The Example class expects 5 annotations
                    ]
                self.example = Example(json_data)
            except Exception as e:
                print(f"Failed to create Example: {e}")
                self.example = None
        
        # Extract clean text from the HTML for text-based processing
        self.clean_text = clean_wikipedia_html(json_data['document_html']) if 'document_html' in json_data else ""
        
    def answer_question(self, question_text=None):
        """Answer a question based on the document content.
        
        Args:
            question_text: The question to answer. If None, use the question from the JSON data.
            
        Returns:
            A dictionary containing:
            - 'answer_text': The extracted answer text if found, otherwise an empty string
            - 'answer_type': Type of answer ('long', 'short', or 'none')
            - 'candidate_index': Index of the answer candidate if found, otherwise -1
            - 'context': Context surrounding the answer
        """
        # Use provided question or the one from JSON data
        question = question_text or self.json_data.get('question_text', '')
        
        # Initialize result dictionary
        result = {
            'answer_text': '',
            'answer_type': 'none',
            'candidate_index': -1,
            'context': '',
            'question': question
        }
        
        # If Example creation failed, try a simple text-based approach
        if self.example is None:
            # Simple fallback: look for longest paragraph that might contain relevant information
            paragraphs = [p for p in self.clean_text.split('\n\n') if len(p) > 50]
            if paragraphs:
                # Very basic relevance scoring - count overlapping words
                question_words = set(question.lower().split())
                scored_paragraphs = []
                for p in paragraphs:
                    p_words = set(p.lower().split())
                    overlap = len(question_words.intersection(p_words))
                    scored_paragraphs.append((overlap, len(p_words), p))
                
                # Sort by overlap score and then by paragraph length
                scored_paragraphs.sort(key=lambda x: (x[0], -x[1]), reverse=True)
                
                if scored_paragraphs:
                    result['answer_text'] = scored_paragraphs[0][2]
                    result['answer_type'] = 'text'
                    result['context'] = scored_paragraphs[0][2]
            
            return result
            
        # If we have a properly initialized Example, use its candidate information
        if self.example.has_long_answer:
            result['answer_text'] = self.example.long_answer_text
            result['answer_type'] = 'long'
            
            # Find the candidate index that contains this answer
            for i, candidate in enumerate(self.example.candidates):
                if candidate.is_answer:
                    result['candidate_index'] = i
                    result['context'] = candidate.contents
                    break
        
        # If we also have short answers, include them
        if self.example.has_short_answer:
            if result['answer_text'] == '':  # Only override if we don't have a long answer
                result['answer_text'] = self.example.short_answers_text
                result['answer_type'] = 'short'
                
                # Find a candidate that contains this short answer
                for i, candidate in enumerate(self.example.candidates):
                    if candidate.contains_answer:
                        result['candidate_index'] = i
                        result['context'] = candidate.contents
                        break
            else:
                # Add short answer as supplementary info
                result['short_answer'] = self.example.short_answers_text
        
        return result


# Example usage
def demo_question_answerer():
    """Demonstrate the QuestionAnswerer class with sample data."""
    import json
    import jsonlines
    
    # Sample JSON data path
    json_path = 'v1.0-simplified_nq-dev-all.jsonl'
    
    try:
        with jsonlines.open(json_path) as reader:
            for idx, obj in enumerate(reader):
                if idx == 0:  # Just use the first example
                    print(f"Question: {obj['question_text']}")
                    
                    # Create question answerer
                    qa = QuestionAnswerer(obj)
                    
                    # Get answer
                    answer = qa.answer_question()
                    
                    print(f"Answer: {clean_wikipedia_html(answer['answer_text'])}")
                    print(f"Answer type: {answer['answer_type']}")
                    print(f"Context: {clean_wikipedia_html(answer['context'][:200])}...")  # Show first 200 chars
                    # print(f"Context: {answer['context'][:200]}...")  # Show first 200 chars
                    break
    except Exception as e:
        print(f"Demo error: {e}")


if __name__ == "__main__":
    demo_question_answerer()
