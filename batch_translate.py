#!/usr/bin/env python
"""
Batch translation script for new languages.
Runs bulk_translate in manageable batches to avoid timeouts.
"""
import os
import sys
import subprocess
import time
from pathlib import Path

# Add Django project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'benefits.settings')
import django
django.setup()

from translations.models import Translation

def count_untranslated(language_code):
    """Count translations that need to be translated for a language"""
    count = 0
    for trans in Translation.objects.all()[:100]:  # Sample first 100
        try:
            trans.set_current_language(language_code)
            if not trans.text or trans.text.strip() == '' or trans.text == 'None':
                count += 1
        except:
            count += 1
    return count

def run_batch_translate(language_code, batch_size=50, max_batches=20):
    """Run bulk_translate in batches for a specific language"""
    print(f"\n=== Batch translating to {language_code} ===")
    
    batch_num = 0
    total_processed = 0
    
    while batch_num < max_batches:
        batch_num += 1
        print(f"\nBatch {batch_num}/{max_batches} for {language_code}...")
        
        # Count untranslated before
        before_count = count_untranslated(language_code)
        
        # Run bulk translate
        cmd = [
            'python', 'manage.py', 'bulk_translate',
            f'--lang={language_code}',
            f'--limit={batch_size}'
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)  # 5 min timeout
            if result.returncode != 0:
                print(f"Error in batch {batch_num}: {result.stderr}")
                break
                
            # Count untranslated after
            after_count = count_untranslated(language_code)
            processed_this_batch = before_count - after_count
            total_processed += processed_this_batch
            
            print(f"Processed ~{processed_this_batch} translations this batch")
            
            # If no progress, we're done
            if processed_this_batch <= 0:
                print(f"No more translations to process for {language_code}")
                break
                
            # Small delay to be nice to Google Translate API
            time.sleep(2)
            
        except subprocess.TimeoutExpired:
            print(f"Batch {batch_num} timed out, continuing...")
            continue
        except Exception as e:
            print(f"Error in batch {batch_num}: {e}")
            break
    
    print(f"Total processed for {language_code}: ~{total_processed} translations")
    return total_processed

def main():
    """Run batch translation for all new languages"""
    new_languages = ['pl', 'tl', 'ko', 'ur']
    language_names = {
        'pl': 'Polish',
        'tl': 'Tagalog', 
        'ko': 'Korean',
        'ur': 'Urdu'
    }
    
    print("Starting batch translation for new languages...")
    print("This may take 30-60 minutes depending on the number of translations.")
    
    total_all_languages = 0
    
    for lang_code in new_languages:
        lang_name = language_names[lang_code]
        print(f"\n{'='*50}")
        print(f"Starting {lang_name} ({lang_code})")
        
        processed = run_batch_translate(lang_code, batch_size=50)
        total_all_languages += processed
        
        print(f"Completed {lang_name}: ~{processed} translations")
    
    print(f"\n{'='*50}")
    print(f"BATCH TRANSLATION COMPLETE")
    print(f"Total translations processed: ~{total_all_languages}")
    print("You can now test the language switching in the frontend.")

if __name__ == "__main__":
    main()