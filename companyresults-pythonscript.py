import pandas as pd
import requests
from bs4 import BeautifulSoup
import openai  #  import the openai module

# Set up OpenAI API key
api_key = 'not my real key'
openai.api_key = api_key  # Set the API key

# Read the Excel file
excel_file = '/Users/serenatheobald/Downloads/companyresults.xlsx'
df = pd.read_excel(excel_file)

keywords = [
    'sponsorship', 'international employees', 'H-1B visas', 'H1B', 'work visa',
    'employment visa', 'work permit', 'visa sponsorship', 'immigration', 'global talent',
    'foreign workers', 'skilled immigrants', 'visa program', 'H-1B program', 'OPT',
    'Optional Practical Training', 'STEM OPT', 'employment-based visa', 'E-3 visa', 'TN visa',
    'L-1 visa', 'O-1 visa', 'foreign nationals', 'international recruitment', 'visa application',
    'green card', 'permanent residency', 'H-2B visa', 'J-1 visa', 'labor certification',
    'international hiring', 'temporary work visa', 'non-immigrant visa', 'H1B cap', 'H1B lottery',
    'H1B petitions', 'sponsor H1B', 'global workforce', 'employment authorization', 'H1B employers',
    'H1B sponsorship', 'H1B renewal', 'H1B transfer'
]
# Set headers to mimic a browser request
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
}

def check_company_website(url):
    try:
        # Ensure the URL starts with 'http://' or 'https://'
        if not url.startswith(('http://', 'https://')):
            url = 'http://' + url

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            text = soup.get_text().lower()  # convert to lower case for case-insensitive search
            for keyword in keywords:
                if keyword.lower() in text:
                    print(f'Keyword "{keyword}" found in {url}')
                    return True
            # Check for links related to sponsorships, international employees, and H-1B visas
            links = soup.find_all('a')
            for link in links:
                for keyword in keywords:
                    if keyword.lower() in link.get('href', ''):
                        print(f'Found a link related to "{keyword}" in {url}: {link.get("href")}')
                        return True
        else:
            print(f'Failed to retrieve {url} with status code {response.status_code}')
    except requests.exceptions.RequestException as e:
        print(f'Error fetching {url}: {e}')
    return False

# Iterate through the first 10 companies in the excel file
for index, row in df.head(10).iterrows():
    company_name = row['Company Name']
    company_website = row['URL/Web Address']

    # Fixing URLs starting with 'http://https://' to 'https://'
    if company_website.startswith('http://https://'):
        company_website = company_website.replace('http://https://', 'https://')

    print(f'Checking {company_name} website: {company_website}')
    if check_company_website(company_website):
        print(f'{company_name} has relevant information.')
    else:
        print(f'No relevant information found for {company_name}.')

    # Use OpenAI API to generate text related to the company (supplement to links/website info)
    prompt = f"Check information about {company_name}."
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are an assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=100
    )
    generated_text = response['choices'][0]['message']['content']
    # Search for keywords in the generated text
    for keyword in keywords:
        if keyword.lower() in generated_text.lower():
            print(f'Keyword "{keyword}" found in generated text for {company_name}.')
            break

print('Done.')
