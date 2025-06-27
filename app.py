from flask import Flask, render_template_string, send_file, jsonify, request
import requests
from bs4 import BeautifulSoup
import csv
import json
import time
import io
import os
from urllib.parse import urljoin, urlparse
from datetime import datetime

app = Flask(__name__)


class MassMailerScraper:
    def __init__(self):
        self.base_url = "https://massmailer.io"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def get_page_content(self, url):
        """Fetch page content with error handling"""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None

    def extract_blog_links(self, html_content, base_url):
        """Extract blog post links from category page"""
        soup = BeautifulSoup(html_content, 'html.parser')
        blog_links = []

        # Find all blog post links
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            if href and '/blog/' in href and href != '/blog/':
                if href.startswith('/'):
                    href = urljoin(base_url, href)
                blog_links.append(href)

        # Remove duplicates and filter valid blog URLs
        unique_links = list(set(blog_links))
        filtered_links = [link for link in unique_links if self.is_valid_blog_url(link)]

        return filtered_links

    def is_valid_blog_url(self, url):
        """Check if URL is a valid blog post URL"""
        parsed = urlparse(url)
        return ('/blog/' in parsed.path and
                parsed.path != '/blog/' and
                not parsed.path.endswith('/blog'))

    def scrape_blog_content(self, blog_url):
        """Scrape individual blog post content"""
        html_content = self.get_page_content(blog_url)
        if not html_content:
            return None

        soup = BeautifulSoup(html_content, 'html.parser')

        # Extract blog data - only include fields we want in CSV
        blog_data = {
            'title': '',
            'url': blog_url,
            'date': '',
            'categories': '',
            'meta_description': '',
            'featured_image': '',
            'content': ''
        }

        # Extract title
        title_tag = soup.find('h1') or soup.find('title')
        if title_tag:
            blog_data['title'] = title_tag.get_text(strip=True)

        # Extract content
        content_div = soup.find('div', class_='post-content') or soup.find('article') or soup.find('div',
                                                                                                   class_='content')
        if content_div:
            # Remove scripts and styles
            for script in content_div(["script", "style"]):
                script.decompose()
            blog_data['content'] = content_div.get_text(strip=True)

        # Extract meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            blog_data['meta_description'] = meta_desc.get('content', '')

        # Extract featured image
        og_image = soup.find('meta', property='og:image')
        if og_image:
            blog_data['featured_image'] = og_image.get('content', '')
        else:
            # Try to find first image in content
            first_img = soup.find('img')
            if first_img:
                img_src = first_img.get('src', '')
                if img_src.startswith('/'):
                    img_src = urljoin(blog_url, img_src)
                blog_data['featured_image'] = img_src

        # Extract date
        date_selectors = [
            'time[datetime]',
            '.date',
            '.post-date',
            '.published'
        ]

        for selector in date_selectors:
            date_elem = soup.select_one(selector)
            if date_elem:
                blog_data['date'] = date_elem.get('datetime') or date_elem.get_text(strip=True)
                break

        # Extract categories
        categories = []
        category_links = soup.find_all('a', href=lambda x: x and ('blog_categories' in x or 'category' in x))
        for cat_link in category_links:
            category = cat_link.get_text(strip=True)
            if category:
                categories.append(category)

        blog_data['categories'] = ', '.join(categories)

        return blog_data

    def scrape_all_blogs(self, category_url):
        """Main function to scrape all blogs from given URL"""
        blogs_data = []

        # Get category page content
        html_content = self.get_page_content(category_url)
        if not html_content:
            return blogs_data

        # Extract base URL for the given site
        parsed_url = urlparse(category_url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

        # Extract blog links
        blog_links = self.extract_blog_links(html_content, base_url)

        # Scrape each blog
        for blog_url in blog_links:
            blog_data = self.scrape_blog_content(blog_url)
            if blog_data:
                blogs_data.append(blog_data)
            time.sleep(1)  # Be respectful

        return blogs_data


# HTML Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Blog Scraper Tool</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            text-align: center;
            margin-bottom: 30px;
        }
        .info-box {
            background: #e3f2fd;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            border-left: 4px solid #2196f3;
        }
        .input-group {
            margin: 20px 0;
        }
        .input-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
            color: #333;
        }
        .input-group input {
            width: 100%;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 6px;
            font-size: 16px;
            box-sizing: border-box;
        }
        .input-group input:focus {
            outline: none;
            border-color: #2196f3;
        }
        .button {
            background: #2196f3;
            color: white;
            padding: 12px 24px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 16px;
            margin: 10px 5px;
            text-decoration: none;
            display: inline-block;
            transition: background 0.3s;
        }
        .button:hover {
            background: #1976d2;
        }
        .button:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        .status {
            margin: 20px 0;
            padding: 10px;
            border-radius: 5px;
            display: none;
        }
        .status.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .status.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .status.info {
            background: #d1ecf1;
            color: #0c5460;
            border: 1px solid #bee5eb;
        }
        .progress {
            width: 100%;
            height: 20px;
            background: #f0f0f0;
            border-radius: 10px;
            overflow: hidden;
            margin: 10px 0;
            display: none;
        }
        .progress-bar {
            height: 100%;
            background: #2196f3;
            width: 0%;
            transition: width 0.3s;
        }
        .results {
            margin-top: 30px;
            display: none;
        }
        .blog-item {
            background: #f9f9f9;
            padding: 15px;
            margin: 10px 0;
            border-radius: 5px;
            border-left: 3px solid #2196f3;
        }
        .blog-title {
            font-weight: bold;
            color: #333;
            margin-bottom: 5px;
        }
        .blog-url {
            color: #666;
            font-size: 14px;
            word-break: break-all;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        .stat-card {
            background: #fff;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .stat-number {
            font-size: 2em;
            font-weight: bold;
            color: #2196f3;
        }
        .stat-label {
            color: #666;
            margin-top: 5px;
        }
        .examples {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin-top: 10px;
        }
        .examples h4 {
            margin: 0 0 10px 0;
            color: #333;
        }
        .examples ul {
            margin: 0;
            padding-left: 20px;
        }
        .examples li {
            margin: 5px 0;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Universal Blog Scraper</h1>

        <div class="info-box">
            <h3>📍 About This Tool</h3>
            <p><strong>Purpose:</strong> Scrape blog posts from any website's blog category or listing page</p>
            <p><strong>How it works:</strong> Enter a URL that contains links to blog posts, and the tool will extract all blog content</p>
            <p><strong>Output:</strong> Download scraped data as CSV file with title, URL, date, categories, content, etc.</p>
        </div>

        <div class="input-group">
            <label for="urlInput">🌐 Enter Blog Category/Listing URL:</label>
            <input type="url" 
                   id="urlInput" 
                   placeholder="e.g., https://example.com/blog or https://massmailer.io/blog_categories/email-deliverability/"
                   value="https://massmailer.io/blog_categories/email-deliverability/">

            <div class="examples">
                <h4>Example URLs:</h4>
                <ul>
                    <li>https://massmailer.io/blog_categories/email-deliverability/</li>
                    <li>https://example.com/blog</li>
                    <li>https://company.com/insights</li>
                    <li>https://website.com/news</li>
                </ul>
            </div>
        </div>

        <div style="text-align: center;">
            <button id="scrapeBtn" class="button" onclick="startScraping()">
                🔍 Start Scraping
            </button>
            <button id="downloadBtn" class="button" onclick="downloadCSV()" style="display:none;">
                📥 Download CSV
            </button>
        </div>

        <div id="status" class="status"></div>
        <div id="progress" class="progress">
            <div id="progressBar" class="progress-bar"></div>
        </div>

        <div id="results" class="results">
            <h3>📊 Scraping Results</h3>
            <div id="stats" class="stats"></div>
            <div id="blogList"></div>
        </div>
    </div>

    <script>
        let scrapedData = [];

        function showStatus(message, type) {
            const statusDiv = document.getElementById('status');
            statusDiv.textContent = message;
            statusDiv.className = `status ${type}`;
            statusDiv.style.display = 'block';
        }

        function showProgress(show) {
            document.getElementById('progress').style.display = show ? 'block' : 'none';
        }

        function updateProgress(percent) {
            document.getElementById('progressBar').style.width = percent + '%';
        }

        function validateUrl(url) {
            try {
                new URL(url);
                return true;
            } catch {
                return false;
            }
        }

        async function startScraping() {
            const urlInput = document.getElementById('urlInput');
            const scrapeBtn = document.getElementById('scrapeBtn');
            const downloadBtn = document.getElementById('downloadBtn');
            const url = urlInput.value.trim();

            // Validate URL
            if (!url) {
                showStatus('❌ Please enter a URL', 'error');
                return;
            }

            if (!validateUrl(url)) {
                showStatus('❌ Please enter a valid URL', 'error');
                return;
            }

            scrapeBtn.disabled = true;
            scrapeBtn.textContent = '🔄 Scraping...';
            downloadBtn.style.display = 'none';

            showStatus('🚀 Starting scraping process...', 'info');
            showProgress(true);
            updateProgress(10);

            try {
                const response = await fetch('/scrape', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ url: url })
                });

                updateProgress(50);

                if (!response.ok) {
                    throw new Error('Scraping failed');
                }

                const data = await response.json();
                updateProgress(100);

                if (data.success) {
                    scrapedData = data.blogs;
                    showStatus(`✅ Successfully scraped ${data.blogs.length} blog posts from ${url}!`, 'success');
                    displayResults(data.blogs);
                    downloadBtn.style.display = 'inline-block';
                } else {
                    showStatus('❌ Scraping failed: ' + data.error, 'error');
                }

            } catch (error) {
                showStatus('❌ Error: ' + error.message, 'error');
            }

            scrapeBtn.disabled = false;
            scrapeBtn.textContent = '🔍 Start Scraping';
            setTimeout(() => showProgress(false), 1000);
        }

        function displayResults(blogs) {
            const resultsDiv = document.getElementById('results');
            const statsDiv = document.getElementById('stats');
            const blogListDiv = document.getElementById('blogList');

            // Show stats
            statsDiv.innerHTML = `
                <div class="stat-card">
                    <div class="stat-number">${blogs.length}</div>
                    <div class="stat-label">Total Blogs</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${blogs.filter(b => b.title).length}</div>
                    <div class="stat-label">With Titles</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${blogs.filter(b => b.content).length}</div>
                    <div class="stat-label">With Content</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${blogs.filter(b => b.featured_image).length}</div>
                    <div class="stat-label">With Images</div>
                </div>
            `;

            // Show blog list (limit to first 10 for display)
            const displayBlogs = blogs.slice(0, 10);
            blogListDiv.innerHTML = `
                ${displayBlogs.map(blog => `
                    <div class="blog-item">
                        <div class="blog-title">${blog.title || 'No Title'}</div>
                        <div class="blog-url">${blog.url}</div>
                        ${blog.date ? `<div style="color: #888; font-size: 12px; margin-top: 5px;">📅 ${blog.date}</div>` : ''}
                        ${blog.categories ? `<div style="color: #888; font-size: 12px; margin-top: 5px;">🏷️ ${blog.categories}</div>` : ''}
                    </div>
                `).join('')}
                ${blogs.length > 10 ? `<div style="text-align: center; padding: 10px; color: #666;">... and ${blogs.length - 10} more blogs</div>` : ''}
            `;

            resultsDiv.style.display = 'block';
        }

        async function downloadCSV() {
            try {
                const response = await fetch('/download-csv');
                const blob = await response.blob();

                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `scraped_blogs_${new Date().toISOString().split('T')[0]}.csv`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);

                showStatus('📥 CSV file downloaded successfully!', 'success');
            } catch (error) {
                showStatus('❌ Download failed: ' + error.message, 'error');
            }
        }

        // Allow Enter key to trigger scraping
        document.getElementById('urlInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                startScraping();
            }
        });
    </script>
</body>
</html>
"""

# Global variable to store scraped data
scraped_blogs = []


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/scrape', methods=['POST'])
def scrape_blogs():
    global scraped_blogs
    try:
        data = request.get_json()
        category_url = data.get('url')

        if not category_url:
            return jsonify({
                'success': False,
                'error': 'URL is required'
            })

        scraper = MassMailerScraper()
        scraped_blogs = scraper.scrape_all_blogs(category_url)

        return jsonify({
            'success': True,
            'blogs': scraped_blogs,
            'count': len(scraped_blogs),
            'source_url': category_url
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


@app.route('/download-csv')
def download_csv():
    global scraped_blogs

    if not scraped_blogs:
        return "No data available. Please scrape first.", 400

    # Create CSV in memory
    output = io.StringIO()
    fieldnames = ['title', 'url', 'date', 'categories', 'meta_description', 'featured_image', 'content']
    writer = csv.DictWriter(output, fieldnames=fieldnames)

    writer.writeheader()
    for blog in scraped_blogs:
        writer.writerow(blog)

    # Create response
    mem = io.BytesIO()
    mem.write(output.getvalue().encode('utf-8'))
    mem.seek(0)

    filename = f"scraped_blogs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return send_file(
        mem,
        as_attachment=True,
        download_name=filename,
        mimetype='text/csv'
    )


@app.route('/api/status')
def api_status():
    global scraped_blogs
    return jsonify({
        'status': 'running',
        'scraped_count': len(scraped_blogs),
        'timestamp': datetime.now().isoformat()
    })


if __name__ == '__main__':
    print("🚀 Starting Universal Blog Scraper Web App...")
    print("📍 Open your browser and go to: http://localhost:5000")
    print("⚡ Press Ctrl+C to stop the server")

    app.run(debug=True, host='0.0.0.0', port=5000)
