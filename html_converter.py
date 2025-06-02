import markdown
import re

def create_html_from_readme(md_file_path, html_file_path, static_folder_name="static"):
    """
    Converts a Markdown file (README.md) to a styled HTML page.

    Args:
        md_file_path (str): Path to the input Markdown file.
        html_file_path (str): Path to save the output HTML file.
        static_folder_name (str): Name of the folder containing static assets like images.
                                  This script assumes this folder will be in the same
                                  directory as the output HTML file.
    """
    try:
        with open(md_file_path, 'r', encoding='utf-8') as f:
            md_content = f.read()
    except FileNotFoundError:
        print(f"Error: Markdown file not found at {md_file_path}")
        return

    # --- Pre-processing for specific sections (like the initial notes) ---
    # Extract and style the initial "Note:" blockquote separately
    # to give it a distinct look from other blockquotes if desired.
    note_pattern = re.compile(r"^(> Note:\s*\n(?:> .+\n)+)", re.MULTILINE)
    initial_notes_html = ""
    
    match = note_pattern.search(md_content)
    if match:
        notes_md = match.group(1)
        # Remove '>' from each line for cleaner HTML conversion of the content
        cleaned_notes_md = "\n".join([line[2:] if line.startswith("> ") else line for line in notes_md.splitlines()])
        # Convert just the notes content to HTML
        notes_content_html = markdown.markdown(cleaned_notes_md, extensions=['extra'])
        initial_notes_html = f'<div class="initial-notes">{notes_content_html}</div>'
        # Remove the notes from the main content to avoid double processing by the main markdown converter
        md_content = note_pattern.sub("", md_content, 1)

    # Convert the rest of the Markdown content to HTML
    # 'extra' includes extensions like 'fenced_code', 'tables', 'attr_list', etc.
    # 'sane_lists' can help with list rendering.
    html_body_content = markdown.markdown(md_content, extensions=['extra', 'sane_lists', 'toc'])

    # --- CSS Styling ---
    # This CSS aims for a clean, academic look. You can heavily customize this.
    css_styles = """
    body {
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; /* Common academic font stack */
        line-height: 1.7;
        margin: 0;
        padding: 0;
        background-color: #f9f9f9; /* Light off-white background */
        color: #333; /* Dark gray for text for readability */
    }
    .container {
        max-width: 900px; /* Optimal width for reading */
        margin: 40px auto;
        padding: 30px 40px;
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        border-radius: 4px;
    }
    /* Special styling for the initial notes */
    .initial-notes {
        background-color: #fffbe6; /* Light yellow */
        border: 1px solid #ffe58f;
        border-left: 5px solid #faad14; /* Prominent left border */
        padding: 15px 20px;
        margin-bottom: 30px;
        border-radius: 4px;
        font-size: 0.95em;
    }
    .initial-notes p {
        margin-top: 0.5em;
        margin-bottom: 0.5em;
    }
    .initial-notes p:first-child {
        margin-top: 0;
    }
    .initial-notes p:last-child {
        margin-bottom: 0;
    }

    /* Header styling (title, authors, links) */
    h1[align="center"] { /* Targets the main title */
        font-size: 2.6em;
        color: #2c3e50; /* Dark blue-gray */
        margin-bottom: 15px;
        font-weight: 600;
        line-height: 1.2;
    }
    p[align="center"] span.author-block {
        display: inline-block; /* Keep authors on the same line if possible */
        margin: 0 5px;
        font-size: 1.1em;
    }
    div.is-size-5.publication-authors {
        text-align: center;
        font-size: 0.95em; /* Slightly smaller for affiliations */
        margin-top: 15px;
        margin-bottom: 25px;
        color: #555;
    }
    div.is-size-5.publication-authors span.author-block {
        display: block; /* Affiliations and notes below authors */
        margin-top: 4px;
        font-size: 0.9em;
    }
    div.is-size-5.publication-authors sup {
        color: #007bff; /* Highlight superscripts */
    }
    p[align="center"] a { /* For Paper | Homepage | Dataset links */
        margin: 0 15px;
        font-size: 1.15em;
        text-decoration: none;
        color: #007bff; /* Standard link blue */
        font-weight: 500;
    }
    p[align="center"] a:hover {
        text-decoration: underline;
    }

    /* General content styling */
    h2 {
        font-size: 1.8em;
        color: #34495e; /* Slightly lighter blue-gray for section titles */
        border-bottom: 2px solid #ecf0f1; /* Light underline */
        padding-bottom: 10px;
        margin-top: 40px;
        margin-bottom: 20px;
        font-weight: 500;
    }
    h3 {
        font-size: 1.4em;
        color: #34495e;
        margin-top: 30px;
        margin-bottom: 15px;
        font-weight: 500;
    }
    p {
        margin-bottom: 1em;
        text-align: justify; /* Justified text for a formal look */
    }
    a {
        color: #2980b9; /* Slightly darker blue for links in text */
        text-decoration: none;
    }
    a:hover {
        text-decoration: underline;
    }
    img {
        max-width: 100%;
        height: auto;
        display: block;
        margin: 25px auto;
        border-radius: 4px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.1);
    }
    /* Code blocks (e.g., BibTeX) */
    pre {
        background-color: #2d2d2d; /* Dark background for code */
        color: #f0f0f0; /* Light text for code */
        padding: 20px;
        border-radius: 5px;
        overflow-x: auto;
        font-family: 'Menlo', 'Consolas', 'Courier New', monospace;
        font-size: 0.9em;
        line-height: 1.5;
        white-space: pre-wrap;       /* css-3 */
        white-space: -moz-pre-wrap;  /* Mozilla, since 1999 */
        white-space: -pre-wrap;      /* Opera 4-6 */
        white-space: -o-pre-wrap;    /* Opera 7 */
        word-wrap: break-word;       /* Internet Explorer 5.5+ */
    }
    code { /* For inline code, if any */
        font-family: 'Menlo', 'Consolas', 'Courier New', monospace;
        background-color: #ecf0f1; /* Light gray background for inline code */
        color: #c0392b; /* Reddish color for inline code */
        padding: 0.2em 0.4em;
        border-radius: 3px;
        font-size: 0.9em;
    }
    /* Table styling */
    table {
        border-collapse: collapse;
        width: 100%;
        margin-bottom: 25px;
        font-size: 0.95em;
        border: 1px solid #ddd;
    }
    th, td {
        border: 1px solid #ddd;
        padding: 10px 12px;
        text-align: left;
    }
    th {
        background-color: #f2f2f2; /* Light gray for table headers */
        font-weight: 600;
    }
    tr:nth-child(even) {
        background-color: #f9f9f9; /* Zebra striping for rows */
    }
    /* Blockquote styling (for any other blockquotes) */
    blockquote {
        border-left: 4px solid #bdc3c7; /* Gray left border */
        padding: 10px 20px;
        margin: 20px 0;
        background-color: #f8f9fa;
        color: #555;
        font-style: italic;
    }
    ul, ol {
        padding-left: 20px; /* Indent lists */
    }
    li {
        margin-bottom: 0.5em;
    }
    """

    # Extract title from the first H1 tag for the <title> tag in HTML head
    # The README has <h1 align="center">Compliance-to-Code...</h1>
    title_match = re.search(r'<h1[^>]*>(.*?)<\/h1>', html_body_content, re.IGNORECASE)
    html_title = "Research Paper" # Default title
    if title_match:
        html_title = title_match.group(1).strip()
        # Remove any potential HTML tags from the title if complex HTML was inside h1
        html_title = re.sub('<[^<]+?>', '', html_title)


    # --- Construct the Full HTML Page ---
    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html_title}</title>
    <style>
    {css_styles}
    </style>
</head>
<body>
    <div class="container">
        {initial_notes_html}
        {html_body_content}
    </div>
</body>
</html>"""

    try:
        with open(html_file_path, 'w', encoding='utf-8') as f:
            f.write(full_html)
        print(f"Successfully converted '{md_file_path}' to '{html_file_path}'")
        print(f"IMPORTANT: Ensure the '{static_folder_name}' folder (containing your images) is in the same directory as '{html_file_path}' for images to display correctly.")
    except IOError:
        print(f"Error: Could not write HTML file to {html_file_path}")

# --- How to use ---
if __name__ == "__main__":
    
    readme_file = "README.md"  # Path to your README file
    output_html_file = "paper_homepage.html" # Desired output HTML file name
    
    
    import os
    if not os.path.exists(readme_file):
        print(f"Please ensure '{readme_file}' exists in the current directory or provide the correct path.")
    else:
        create_html_from_readme(readme_file, output_html_file, static_folder_name="static")