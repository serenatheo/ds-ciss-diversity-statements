import requests
from bs4 import BeautifulSoup
import pandas as pd
import openai
from weasyprint import HTML
import math
import asyncio
import re
import json
import httpx
from urllib.parse import urlencode
import time

# Set up OpenAI API key
api_key = 'not my real key'
openai.api_key = api_key

# Read the Excel file
excel_file = '/Users/serenatheobald/Downloads/companyresults.xlsx'
df = pd.read_excel(excel_file)

keywords = [
    'sponsorship', 'international employees', 'H-1B visas', 'H1B', 'work visa',
    'employment visa', 'work permit', 'visa sponsorship', 'immigration', 'global talent',
    'foreign workers', 'skilled immigrants', 'visa program', 'H-1B program',
    'Optional Practical Training', 'STEM OPT', 'employment-based visa', 'E-3 visa', 'TN visa',
    'L-1 visa', 'O-1 visa', 'foreign nationals', 'international recruitment', 'visa application',
    'green card', 'permanent residency', 'H-2B visa', 'J-1 visa', 'labor certification',
    'international hiring', 'temporary work visa', 'non-immigrant visa', 'H1B cap', 'H1B lottery',
    'H1B petitions', 'sponsor H1B', 'global workforce', 'employment authorization', 'H-1B employers',
    'H-1B sponsorship', 'H-1B renewal', 'H-1B transfer', 'foreign', 'visa', 'international', 'international candidate'
]

# Set headers to mimic a browser request
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
}

def check_company_website(url):
    found_links = []
    try:
        if not url.startswith(('http://', 'https://')):
            url = 'http://' + url

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            text = soup.get_text().lower()
            for keyword in keywords:
                if keyword.lower() in text:
                    found_links.append((url, keyword))
                    break

            links = soup.find_all('a')
            for link in links:
                for keyword in keywords:
                    if keyword.lower() in link.get('href', ''):
                        found_links.append((link.get('href'), keyword))
                        break
        else:
            print(f'Failed to retrieve {url} with status code {response.status_code}')
    except requests.exceptions.RequestException as e:
        print(f'Error fetching {url}: {e}')
    return found_links

# Function to scrape LinkedIn jobs
def scrape_linkedin_jobs(company_name):
    job_ids = []
    target_url = 'https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={}&location=United%20States&start={}'
    number_of_jobs = 117
    number_of_loops = math.ceil(number_of_jobs / 25)
    
    for i in range(number_of_loops):
        try:
            res = requests.get(target_url.format(company_name, i * 25))
            soup = BeautifulSoup(res.text, 'html.parser')
            all_jobs_on_this_page = soup.find_all("li")
            
            for job in all_jobs_on_this_page:
                job_id_element = job.find("div", {"class": "base-card"})
                if job_id_element:
                    job_id = job_id_element.get('data-entity-urn').split(":")[3]
                    job_ids.append(job_id)
            
            # Delay to avoid sending too many requests in a short period
            time.sleep(2)
        
        except requests.exceptions.RequestException as e:
            print(f'Error fetching LinkedIn job page {i}: {e}')
            time.sleep(10)  # Wait before retrying

    job_details = []
    job_detail_url = 'https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{}'
    
    for job_id in job_ids:
        job_url = job_detail_url.format(job_id)
        try:
            resp = requests.get(job_url)
            soup = BeautifulSoup(resp.text, 'html.parser')
            job_info = {}
            
            try:
                job_info["company"] = soup.find("div", {"class": "top-card-layout__card"}).find("a").find("img").get('alt')
            except AttributeError:
                job_info["company"] = None
            
            try:
                job_info["job_title"] = soup.find("div", {"class": "top-card-layout__entity-info"}).find("a").text.strip()
            except AttributeError:
                job_info["job_title"] = None
            
            try:
                job_info["level"] = soup.find("ul", {"class": "description__job-criteria-list"}).find("li").text.replace("Seniority level", "").strip()
            except AttributeError:
                job_info["level"] = None
            
            # Check for keywords in job description
            job_description = soup.find("div", {"class": "show-more-less-html__markup"})
            keywords_detected = [keyword for keyword in keywords if keyword.lower() in job_description.text.lower()] if job_description else []
            job_info["international_workers"] = True if keywords_detected else False
            job_info["keywords_detected"] = keywords_detected

            job_details.append(job_info)
            time.sleep(2)  # Delay to avoid sending too many requests in a short period
        
        except requests.exceptions.RequestException as e:
            print(f'Error fetching LinkedIn job detail for job ID {job_id}: {e}')
            time.sleep(10)  # Wait before retrying

    return job_details



# Create a DataFrame to store the results
results = []

# Iterate through the first 10 companies in the Excel file
for index, row in df.head(5).iterrows():
    company_name = row['Company Name']
    company_website = row['URL/Web Address']

    # Fixing URLs starting with 'http://https://' to 'https://'
    if company_website.startswith('http://https://'):
        company_website = company_website.replace('http://https://', 'https://')

    print(f'Checking {company_name} website: {company_website}')
    found_links = check_company_website(company_website)

    # Use OpenAI API to generate text related to the company (supplement to links/website info)
    prompt = f"What does the career website of {company_name} U.S. say about international candidates? Additionally, find specific links on the company's website that mention international workers and visas."
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are an assistant assigned to find information about international workers for different Fortune 500 Companies. For example, here is the career site mentioning international candidates for Walmart: https://careers.walmart.com/faqs. Do this for other companies I'm iterating over too. In addition, find specific links on the company's website that include that information."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=500
    )
    generated_text = response['choices'][0]['message']['content']

    for keyword in keywords:
        if keyword.lower() in generated_text.lower():
            found_links.append(('OpenAI generated text', keyword))
            break

    # Scrape LinkedIn jobs
    linkedin_jobs = scrape_linkedin_jobs(company_name)


    result = {
        'Company Name': company_name,
        'URL/Web Address': company_website,
        'Found Links': found_links,
        'OpenAI Generated Text': generated_text,
        'LinkedIn Jobs': linkedin_jobs,
        
    }

    results.append(result)

# Convert the results to a DataFrame
result_df = pd.DataFrame(results)

# Save the results to a new Excel file
output_file = '/Users/serenatheobald/Downloads/companyresults_with_job_data.xlsx'
result_df.to_excel(output_file, index=False)

# Generate a PDF from the results
html_content = result_df.to_html()
pdf_file = '/Users/serenatheobald/Downloads/companyresults_with_job_data.pdf'
HTML(string=html_content).write_pdf(pdf_file)

print('Results saved to Excel and PDF.')