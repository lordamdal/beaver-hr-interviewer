# app/utils/resume_parser.py

import PyPDF2
import docx
import spacy
import re
from typing import Dict, List, Optional, Any
import logging
from pathlib import Path
import tempfile
import json
from datetime import datetime
import email_validator
from spacy.tokens import Doc
import pandas as pd
from collections import defaultdict

logger = logging.getLogger(__name__)

class ResumeParser:
    def __init__(self):
        """Initialize the resume parser"""
        try:
            # Load SpaCy model for NER
            self.nlp = spacy.load("en_core_web_lg")
            
            # Add custom pipeline components
            self.nlp.add_pipe("skill_matcher", after="ner")
            self.nlp.add_pipe("education_extractor", after="skill_matcher")
            self.nlp.add_pipe("experience_extractor", after="education_extractor")
            
            # Load skills database
            self.skills_db = self._load_skills_database()
            
            # Compile regex patterns
            self._compile_patterns()
            
        except Exception as e:
            logger.error(f"Failed to initialize resume parser: {str(e)}")
            raise

    def _load_skills_database(self) -> Dict[str, List[str]]:
        """Load and return skills database"""
        try:
            # This would typically load from a JSON file or database
            # For now, we'll use a basic dictionary
            return {
                "programming_languages": [
                    "Python", "Java", "JavaScript", "C++", "C#", "Ruby", "PHP",
                    "Swift", "Kotlin", "Go", "Rust", "TypeScript"
                ],
                "frameworks": [
                    "React", "Angular", "Vue.js", "Django", "Flask", "Spring",
                    "Node.js", "Express.js", "TensorFlow", "PyTorch"
                ],
                "databases": [
                    "MySQL", "PostgreSQL", "MongoDB", "SQLite", "Oracle",
                    "Redis", "Cassandra", "ElasticSearch"
                ],
                "tools": [
                    "Git", "Docker", "Kubernetes", "Jenkins", "AWS", "Azure",
                    "GCP", "Linux", "Jira", "Confluence"
                ],
                "soft_skills": [
                    "Leadership", "Communication", "Problem Solving",
                    "Team Work", "Time Management", "Critical Thinking"
                ]
            }
        except Exception as e:
            logger.error(f"Failed to load skills database: {str(e)}")
            return {}

    def _compile_patterns(self):
        """Compile regex patterns for parsing"""
        self.patterns = {
            'email': re.compile(r'[\w\.-]+@[\w\.-]+\.\w+'),
            'phone': re.compile(r'[\+\(]?[1-9][0-9 .\-\(\)]{8,}[0-9]'),
            'education': re.compile(r'(?i)(bachelor|master|phd|b\.?s\.?|m\.?s\.?|ph\.?d\.?)'),
            'date': re.compile(r'(?i)(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[\s\-]?\d{4}'),
            'url': re.compile(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s]*')
        }

    def parse(self, file_obj: Any) -> Optional[Dict[str, Any]]:
        """
        Parse resume file and extract information
        
        Args:
            file_obj: File object (PDF or DOCX)
            
        Returns:
            Dictionary containing parsed resume information
        """
        try:
            # Extract text from file
            text = self._extract_text(file_obj)
            if not text:
                raise ValueError("No text could be extracted from the file")

            # Process text with SpaCy
            doc = self.nlp(text)

            # Extract information
            parsed_data = {
                'basic_info': self._extract_basic_info(doc),
                'contact_info': self._extract_contact_info(text),
                'education': self._extract_education(doc),
                'experience': self._extract_experience(doc),
                'skills': self._extract_skills(doc),
                'languages': self._extract_languages(doc),
                'projects': self._extract_projects(doc),
                'certifications': self._extract_certifications(doc),
                'summary': self._generate_summary(doc),
                'metadata': {
                    'parsed_at': datetime.utcnow().isoformat(),
                    'parser_version': '1.0.0'
                }
            }

            # Validate parsed data
            self._validate_parsed_data(parsed_data)

            return parsed_data

        except Exception as e:
            logger.error(f"Failed to parse resume: {str(e)}")
            return None

    def _extract_text(self, file_obj: Any) -> str:
        """Extract text from resume file"""
        try:
            # Get file extension
            filename = file_obj.name.lower()
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file.write(file_obj.read())
                temp_path = temp_file.name

            if filename.endswith('.pdf'):
                return self._extract_from_pdf(temp_path)
            elif filename.endswith(('.docx', '.doc')):
                return self._extract_from_docx(temp_path)
            else:
                raise ValueError("Unsupported file format")

        finally:
            # Cleanup temporary file
            Path(temp_path).unlink()

    def _extract_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF file"""
        text = ""
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        return text

    def _extract_from_docx(self, file_path: str) -> str:
        """Extract text from DOCX file"""
        doc = docx.Document(file_path)
        return "\n".join([paragraph.text for paragraph in doc.paragraphs])

    def _extract_basic_info(self, doc: Doc) -> Dict[str, str]:
        """Extract basic information from resume"""
        basic_info = {
            'name': '',
            'title': '',
            'location': ''
        }

        # Extract name (usually first PERSON entity)
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                basic_info['name'] = ent.text
                break

        # Extract job title
        title_patterns = [
            r"(?i)(Senior|Lead|Principal|Junior|Software|Data|Product|Project|Business|Marketing|Sales|HR|Human Resources)[\s\w]+",
            r"(?i)(Engineer|Developer|Scientist|Analyst|Manager|Consultant|Designer|Architect)"
        ]
        
        for pattern in title_patterns:
            matches = re.findall(pattern, doc.text)
            if matches:
                basic_info['title'] = matches[0]
                break

        # Extract location (GPE entities)
        locations = [ent.text for ent in doc.ents if ent.label_ == "GPE"]
        if locations:
            basic_info['location'] = locations[0]

        return basic_info

    def _extract_contact_info(self, text: str) -> Dict[str, str]:
        """Extract contact information"""
        contact_info = {
            'email': '',
            'phone': '',
            'linkedin': '',
            'github': '',
            'website': ''
        }

        # Extract email
        email_matches = self.patterns['email'].findall(text)
        if email_matches:
            contact_info['email'] = email_matches[0]

        # Extract phone
        phone_matches = self.patterns['phone'].findall(text)
        if phone_matches:
            contact_info['phone'] = phone_matches[0]

        # Extract URLs
        urls = self.patterns['url'].findall(text)
        for url in urls:
            if 'linkedin.com' in url:
                contact_info['linkedin'] = url
            elif 'github.com' in url:
                contact_info['github'] = url
            else:
                contact_info['website'] = url

        return contact_info

    def _extract_education(self, doc: Doc) -> List[Dict[str, str]]:
        """Extract education information"""
        education = []
        edu_section = self._find_section(doc.text, ['education', 'academic'])
        
        if edu_section:
            # Process education section
            for sent in doc.sents:
                if self.patterns['education'].search(sent.text):
                    edu_entry = {
                        'degree': '',
                        'institution': '',
                        'date': '',
                        'gpa': ''
                    }
                    
                    # Extract degree
                    degree_match = self.patterns['education'].search(sent.text)
                    if degree_match:
                        edu_entry['degree'] = degree_match.group()
                    
                    # Extract institution (ORG entities)
                    orgs = [ent.text for ent in sent.ents if ent.label_ == "ORG"]
                    if orgs:
                        edu_entry['institution'] = orgs[0]
                    
                    # Extract date
                    date_match = self.patterns['date'].search(sent.text)
                    if date_match:
                        edu_entry['date'] = date_match.group()
                    
                    # Extract GPA
                    gpa_pattern = r'GPA:?\s*(\d+\.\d+)'
                    gpa_match = re.search(gpa_pattern, sent.text)
                    if gpa_match:
                        edu_entry['gpa'] = gpa_match.group(1)
                    
                    education.append(edu_entry)
        
        return education

    def _extract_experience(self, doc: Doc) -> List[Dict[str, Any]]:
        """Extract work experience information"""
        experience = []
        exp_section = self._find_section(doc.text, ['experience', 'work', 'employment'])
        
        if exp_section:
            current_company = None
            current_position = None
            current_dates = None
            current_responsibilities = []
            
            for sent in doc.sents:
                # New company/position detection
                orgs = [ent.text for ent in sent.ents if ent.label_ == "ORG"]
                if orgs:
                    if current_company:
                        # Save previous entry
                        experience.append({
                            'company': current_company,
                            'position': current_position,
                            'dates': current_dates,
                            'responsibilities': current_responsibilities
                        })
                    
                    current_company = orgs[0]
                    current_position = self._extract_position(sent.text)
                    current_dates = self._extract_dates(sent.text)
                    current_responsibilities = []
                elif sent.text.strip().startswith(('â€¢', '-', 'âˆ™')):
                    current_responsibilities.append(sent.text.strip())
            
            # Add last entry
            if current_company:
                experience.append({
                    'company': current_company,
                    'position': current_position,
                    'dates': current_dates,
                    'responsibilities': current_responsibilities
                })
        
        return experience

    def _extract_skills(self, doc: Doc) -> Dict[str, List[str]]:
        """Extract skills information"""
        skills = defaultdict(list)
        
        # Process each category in skills database
        for category, skill_list in self.skills_db.items():
            for skill in skill_list:
                if re.search(rf'\b{skill}\b', doc.text, re.IGNORECASE):
                    skills[category].append(skill)
        
        return dict(skills)

    def _extract_languages(self, doc: Doc) -> List[Dict[str, str]]:
        """Extract language proficiencies"""
        languages = []
        language_section = self._find_section(doc.text, ['languages', 'language skills'])
        
        if language_section:
            language_pattern = r'(?i)(English|Spanish|French|German|Chinese|Japanese|Korean|Russian|Arabic|Portuguese|Italian)[\s\-]*(Native|Fluent|Professional|Intermediate|Basic)'
            matches = re.findall(language_pattern, language_section)
            
            for lang, level in matches:
                languages.append({
                    'language': lang.strip(),
                    'proficiency': level.strip()
                })
        
        return languages

    def _extract_projects(self, doc: Doc) -> List[Dict[str, Any]]:
        """Extract project information"""
        projects = []
        project_section = self._find_section(doc.text, ['projects', 'personal projects'])
        
        if project_section:
            current_project = None
            current_description = []
            current_technologies = []
            
            for sent in doc.sents:
                if sent.text.strip().startswith(('â€¢', '-', 'âˆ™')):
                    if current_project:
                        current_description.append(sent.text.strip())
                else:
                    # New project
                    if current_project:
                        projects.append({
                            'name': current_project,
                            'description': current_description,
                            'technologies': current_technologies
                        })
                    
                    current_project = sent.text.strip()
                    current_description = []
                    current_technologies = self._extract_technologies(sent.text)
            
            # Add last project
            if current_project:
                projects.append({
                    'name': current_project,
                    'description': current_description,
                    'technologies': current_technologies
                })
        
        return projects

    def _extract_certifications(self, doc: Doc) -> List[Dict[str, str]]:
        """Extract certification information"""
        certifications = []
        cert_section = self._find_section(doc.text, ['certifications', 'certificates'])
        
        if cert_section:
            cert_pattern = r'(?i)([\w\s]+certification|certificate)[\s\-]*([\w\s]+)'
            matches = re.findall(cert_pattern, cert_section)
            
            for cert_type, details in matches:
                certifications.append({
                    'name': f"{cert_type} {details}".strip(),
                    'date': self._extract_dates(details)
                })
        
        return certifications

    def _generate_summary(self, doc: Doc) -> str:
        """Generate a summary of the resume"""
        # Use SpaCy's text rank algorithm to generate summary
        from spacy.lang.en.stop_words import STOP_WORDS
        from string import punctuation
        from heapq import nlargest

        keyword_puncts = punctuation + '\n'
        word_frequencies = {}
        
        for word in doc:
            if word.text.lower() not in STOP_WORDS and word.text.lower() not in keyword_puncts:
                if word.text not in word_frequencies.keys():
                    word_frequencies[word.text] = 1
                else:
                    word_frequencies[word.text] += 1

        max_frequency = max(word_frequencies.values())
        for word in word_frequencies.keys():
            word_frequencies[word] = word_frequencies[word]/max_frequency

        sentence_tokens = [sent for sent in doc.sents]
        sentence_scores = {}
        for sent in sentence_tokens:
            for word in sent:
                if word.text.lower() in word_frequencies.keys():
                    if sent not in sentence_scores.keys():
                        sentence_scores[sent] = word_frequencies[word.text.lower()]
                    else:
                        sentence_scores[sent] += word_frequencies[word.text.lower()]

        select_length = min(3, len(sentence_tokens))
        summary = nlargest(select_length, sentence_scores, key=sentence_scores.get)
        
        return " ".join([sent.text for sent in summary])

    def _find_section(self, text: str, section_keywords: List[str]) -> Optional[str]:
        """Find and return specific section from text"""
        lines = text.split('\n')
        section_start = -1
        section_end = -1
        
        for i, line in enumerate(lines):
            # Check if line contains section keyword
            if any(keyword.lower() in line.lower() for keyword in section_keywords):
                section_start = i
                continue
            
            # Find next section (indicates end of current section)
            if section_start != -1 and line.strip() and line[0].isupper():
                section_end = i
                break
        
        if section_start != -1:
            if section_end == -1:
                section_end = len(lines)
            return '\n'.join(lines[section_start:section_end])
        
        return None

    def _extract_position(self, text: str) -> Optional[str]:
        """Extract position title from text"""
        position_patterns = [
            r"(?i)(Senior|Lead|Principal|Junior|Software|Data|Product|Project|Business|Marketing|Sales|HR|Human Resources)[\s\w]+",
            r"(?i)(Engineer|Developer|Scientist|Analyst|Manager|Consultant|Designer|Architect)"
        ]
        
        for pattern in position_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group()
        
        return None

    def _extract_dates(self, text: str) -> Optional[str]:
        """Extract date ranges from text"""
        date_pattern = r'(?i)(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[\s\-]?\d{4}'
        dates = re.findall(date_pattern, text)
        
        if len(dates) >= 2:
            return f"{dates[0]} - {dates[1]}"
        elif len(dates) == 1:
            return f"{dates[0]} - Present"
        
        return None

    def _extract_technologies(self, text: str) -> List[str]:
        """Extract technology mentions from text"""
        technologies = []
        
        # Check against skills database
        for category, skills in self.skills_db.items():
            for skill in skills:
                if re.search(rf'\b{skill}\b', text, re.IGNORECASE):
                    technologies.append(skill)
        
        return technologies

    def _validate_parsed_data(self, data: Dict[str, Any]) -> None:
        """Validate parsed resume data"""
        try:
            # Validate basic info
            if not data['basic_info']['name']:
                logger.warning("No name found in resume")
            
            # Validate contact info
            if data['contact_info']['email']:
                email_validator.validate_email(data['contact_info']['email'])
            
            # Validate education
            if not data['education']:
                logger.warning("No education information found")
            
            # Validate experience
            if not data['experience']:
                logger.warning("No experience information found")
            
            # Validate skills
            if not any(data['skills'].values()):
                logger.warning("No skills found in resume")

        except Exception as e:
            logger.error(f"Data validation error: {str(e)}")
            raise

    def export_to_json(self, parsed_data: Dict[str, Any], output_path: str) -> bool:
        """Export parsed data to JSON file"""
        try:
            with open(output_path, 'w') as f:
                json.dump(parsed_data, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to export data: {str(e)}")
            return False

    def export_to_structured_format(self, parsed_data: Dict[str, Any], 
                                  format_type: str = 'json') -> Optional[str]:
        """Export parsed data to various structured formats"""
        try:
            if format_type == 'json':
                return json.dumps(parsed_data, indent=2)
            elif format_type == 'xml':
                import dicttoxml
                return dicttoxml.dicttoxml(parsed_data, custom_root='resume').decode()
            elif format_type == 'yaml':
                import yaml
                return yaml.dump(parsed_data)
            else:
                raise ValueError(f"Unsupported format type: {format_type}")
        except Exception as e:
            logger.error(f"Failed to export to {format_type}: {str(e)}")
            return None

# Usage example
if __name__ == "__main__":
    parser = ResumeParser()
    
    # Test with a sample resume file
    test_file_path = "path/to/test/resume.pdf"
    if Path(test_file_path).exists():
        with open(test_file_path, 'rb') as file:
            parsed_data = parser.parse(file)
            
            if parsed_data:
                print("Parsed Resume Data:")
                print(json.dumps(parsed_data, indent=2))
                
                # Export to different formats
                parser.export_to_json(parsed_data, "resume_parsed.json")
                xml_output = parser.export_to_structured_format(parsed_data, 'xml')
                yaml_output = parser.export_to_structured_format(parsed_data, 'yaml')