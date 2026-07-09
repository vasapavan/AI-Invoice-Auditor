"""
Extractor Agent - Extracts data from PDF, DOCX, PNG invoices using LLM
"""
import pdfplumber
from docx import Document
from PIL import Image
import pytesseract
import yaml
import json
from pathlib import Path
from litellm import completion

class ExtractorAgent:
    def __init__(self):
        # Load persona configuration
        config_path = Path(__file__).parent.parent / "configs" / "persona_extraction_agent.yaml"
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        self.model = self.config['model']
        self.temperature = self.config['temperature']
        self.max_tokens = self.config['max_tokens']
    
    def extract_raw_text(self, file_path):
        """Extract raw text from invoice file"""
        print(f"Extracting raw text from: {file_path}")
        
        if file_path.endswith('.pdf'):
            with pdfplumber.open(file_path) as pdf:
                text = pdf.pages[0].extract_text()
        elif file_path.endswith('.docx'):
            doc = Document(file_path)
            text = "\n".join([para.text for para in doc.paragraphs])
        elif file_path.endswith(('.png', '.jpg', '.jpeg')):
            print("Using OCR (Tesseract)...")
            image = Image.open(file_path)
            text = pytesseract.image_to_string(image)
        else:
            raise ValueError("Unsupported file format")
        
        print(f"Extracted: {text}")
        return text
    
    def extract_structured_data(self, text):
        """Extract structured invoice data using LLM"""
        print(f"Extracting structured data using LLM...")
        
        try:
            prompt = self.config['extraction_prompt'].format(text=text)
            
            response = completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.config['system_prompt']},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            # Parse JSON response
            json_str = response.choices[0].message.content.strip()
            
            # Clean response (remove markdown code blocks if present)
            if json_str.startswith('```'):
                json_str = json_str.split('```')[1]
                if json_str.startswith('json'):
                    json_str = json_str[4:]
                json_str = json_str.strip()
            
            data = json.loads(json_str)
            # Add raw_text to data
            data['raw_text'] = text
            print(f"Extracted Structured Invoice: ", data)
            return data
            
        except Exception as e:
            print(f"LLM extraction error: {e}")

