"""
Translation Agent - Translates invoices using AWS Bedrock Cohere Command R+
"""
import os
import yaml
from pathlib import Path
from litellm import completion

class TranslationAgent:
    def __init__(self):
        # Load persona configuration
        config_path = Path(__file__).parent.parent / "configs" / "persona_translation_agent.yaml"
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        self.model = self.config['model']
        self.temperature = self.config['temperature']
        self.max_tokens = self.config['max_tokens']
        
        # Set AWS credentials from environment
        os.environ['AWS_REGION_NAME'] = os.getenv('AWS_REGION', 'us-east-1')
    
    def detect_language(self, text):
        """Detect language using LLM"""
        # Using first 500 characters for detection
        sample = text[:500] if len(text) > 500 else text
        prompt = self.config['language_detection_prompt'].format(text=sample)
        
        response = completion(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=50
        )
        
        detected_lang = response.choices[0].message.content.strip()
        return detected_lang
    
    def assess_translation_confidence(self, original_text, translated_text, source_language):
        """Use LLM to assess translation quality and confidence"""
        confidence_prompt = self.config['confidence_assessment_prompt'].format(
            source_language=source_language,
            original_text=original_text,
            translated_text=translated_text
        )
        try:
            response = completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.config['confidence_system_prompt']},
                    {"role": "user", "content": confidence_prompt}
                ],
                temperature=0.1,
                max_tokens=100
            )
            confidence_response = response.choices[0].message.content.strip()
            confidence_score = float(confidence_response)
            return confidence_score
            
        except Exception as e:
            print(f"Confidence assessment error: {e}")
            return 0.8  # Default moderate confidence
    
    def translate_raw_text(self, text):
        """Translate raw text to English"""
        detected_lang = self.detect_language(text)
        
        print(f"Language detected: {detected_lang}")
        if detected_lang.lower() == 'english':
            print("No translation needed")
            return {
                'translated_text': text,
                'original_language': 'English',
                'translation_confidence': 1.0,
                'was_translated': False
            }
        
        # Translate non-English text
        print(f"Translating from {detected_lang} to English...")
        
        try:
            prompt = self.config['translation_prompt'].format(
                source_language=detected_lang,
                text=text
            )
            
            response = completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.config['system_prompt']},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            translated_text = response.choices[0].message.content.strip()
            
            # Use LLM to assess translation confidence
            print("Assessing translation confidence...")
            confidence_score = self.assess_translation_confidence(
                original_text=text,
                translated_text=translated_text,
                source_language=detected_lang
            )
            print(f"Translation confidence: {confidence_score:.2f}")
            
            print("Translation complete")
            return {
                'translated_text': translated_text,
                'original_text': text,
                'original_language': detected_lang,
                'translation_confidence': confidence_score,
                'was_translated': True
            }
            
        except Exception as e:
            print(f"Translation error: {e}")
            print(f"Using original text")
            return {
                'translated_text': text,
                'original_language': detected_lang,
                'translation_confidence': 0.0,
                'was_translated': False
            }
