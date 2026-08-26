import markdown

with open("deep_dive.md", "r") as f:
    text = f.read()

# Very basic markdown conversion (using markdown package if available, else fallback to creating an HTML file that uses marked.js)
html_content = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Razorpay AI Buildathon 2026: Chargeback Verifier Deep Dive</title>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<script type="module">
    import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
    mermaid.initialize({{ startOnLoad: true }});
    
    // Render markdown
    const mdContent = document.getElementById('markdown-content').textContent;
    document.getElementById('content').innerHTML = marked.parse(mdContent);
    
    // Convert text mermaid blocks to div class=mermaid
    document.querySelectorAll('code.language-text').forEach(block => {{
        if(block.textContent.includes('graph TD') || block.textContent.includes('sequenceDiagram')) {{
            const div = document.createElement('div');
            div.className = 'mermaid';
            div.textContent = block.textContent;
            block.parentNode.replaceWith(div);
        }}
    }});
    
    // Replace text codeblocks that are not mermaid with normal pre>code
    setTimeout(() => mermaid.init(), 100);
</script>
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    body {{
        font-family: 'Inter', -apple-system, sans-serif;
        line-height: 1.6;
        color: #1e293b;
        max-width: 850px;
        margin: 0 auto;
        padding: 40px;
        background: #f8fafc;
    }}
    .page {{
        background: white;
        padding: 50px 60px;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
        border-radius: 8px;
    }}
    h1, h2, h3 {{
        color: #0f172a;
        margin-top: 1.5em;
    }}
    h1 {{ border-bottom: 3px solid #e2e8f0; padding-bottom: 10px; font-size: 2.2em; }}
    h2 {{ border-bottom: 1px solid #e2e8f0; padding-bottom: 8px; color: #1e40af; }}
    code {{
        background: #f1f5f9;
        padding: 2px 6px;
        border-radius: 4px;
        font-family: ui-monospace, monospace;
        font-size: 0.9em;
        color: #be123c;
    }}
    pre code {{
        background: transparent;
        color: #e2e8f0;
    }}
    pre {{
        background: #1e293b;
        padding: 16px;
        border-radius: 8px;
        overflow-x: auto;
    }}
    hr {{ border: 0; border-top: 1px solid #e2e8f0; margin: 2em 0; }}
    ul, ol {{ padding-left: 24px; }}
    li {{ margin-bottom: 0.5em; }}
    .cover-page {{ text-align: center; padding: 100px 0; border-bottom: none; }}
    
    @media print {{
        body {{ background: white; padding: 0; max-width: 100%; }}
        .page {{ box-shadow: none; padding: 0; border-radius: 0; }}
        h1, h2 {{ page-break-after: avoid; }}
        pre, .mermaid {{ page-break-inside: avoid; }}
        hr {{ display: none; }}
        h1 {{ margin-top: 0; }}
    }}
</style>
</head>
<body>
    <div class="page">
        <div id="content"></div>
    </div>
    <script type="text/markdown" id="markdown-content">
{text.replace('`', '`').replace('script', 'scr\\ipt')}
    </script>
</body>
</html>
"""
with open("Razorpay_AI_Buildathon_Chargeback_Evidence_Deep_Dive.html", "w") as f:
    f.write(html_content)
