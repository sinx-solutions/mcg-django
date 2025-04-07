import PyPDF2

file_path = '/Users/sanchaythalnerkar/root-turborepo/apps/api/resumes/resumesanchay.pdf'

def analyze_pdf(pdf_path):
    """Analyze a PDF file and extract information using PyPDF2."""
    print(f"Analyzing PDF: {pdf_path}")
    print("-" * 50)
    
    try:
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            
            # 1. Extract and print metadata
            print("\n📄 Document Metadata:")
            metadata = reader.metadata
            if metadata:
                for key, value in metadata.items():
                    # Remove /AAPL: prefix that often appears in metadata keys
                    cleaned_key = str(key).replace('/AAPL:', '').replace('/', '')
                    print(f"  {cleaned_key}: {value}")
            else:
                print("  No metadata found")
                
            # 2. Print document structure information
            total_pages = len(reader.pages)
            print(f"\n📚 Document Structure:")
            print(f"  • Total pages: {total_pages}")
            
            # 3. Extract text from the first few pages
            print("\n📝 Content Preview:")
            page_samples = min(3, total_pages)  # Preview up to 3 pages
            
            for i in range(page_samples):
                try:
                    page = reader.pages[i]
                    text = page.extract_text()
                    preview = text[:150] + "..." if len(text) > 150 else text
                    preview = preview.replace('\n', ' ')
                    print(f"\n  Page {i+1}:")
                    print(f"  {preview}")
                except Exception as e:
                    print(f"  ⚠️ Error extracting text from page {i+1}: {e}")
            
            # 4. Check for form fields if available
            if hasattr(reader, 'get_fields') and callable(reader.get_fields):
                try:
                    fields = reader.get_fields()
                    if fields:
                        print("\n📋 Form Fields:")
                        for field_name, field_value in fields.items():
                            print(f"  {field_name}: {field_value}")
                    else:
                        print("\n📋 Form Fields: None found")
                except Exception as e:
                    print(f"\n⚠️ Error retrieving form fields: {e}")
                    
    except FileNotFoundError:
        print(f"⚠️ Error: File not found - {pdf_path}")
    except PermissionError:
        print(f"⚠️ Error: Permission denied accessing {pdf_path}")
    except Exception as e:
        print(f"⚠️ Error: {str(e)}")

# Run the analysis
analyze_pdf(file_path)
