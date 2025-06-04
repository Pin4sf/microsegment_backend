import httpx
import re
import logging
from typing import Dict, Any
from bs4 import BeautifulSoup, Tag
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


async def verify_shopify_url(url: str) -> bool:
    """
    Verifies if the given URL is a valid and accessible online store URL.
    Attempts to make an HTTP GET request and checks for a successful status code.
    """
    # Relax the check: simply verify if the URL is accessible
    try:
        # Use a reasonably short timeout for verification
        async with httpx.AsyncClient() as client:
            response = await client.get(url, follow_redirects=True, timeout=10)
            # Check for successful status codes (2xx)
            if response.status_code >= 200 and response.status_code < 300:
                logger.info(
                    f"URL {url} verified as accessible with status code {response.status_code}.")
                return True
            else:
                logger.warning(
                    f"URL {url} returned non-successful status code: {response.status_code}.")
                return False

    except httpx.RequestError as e:
        logger.warning(f"Could not verify URL {url} via HTTP request: {e}")
        return False  # Cannot verify if request fails
    except Exception as e:
        logger.warning(
            f"An unexpected error occurred during URL verification for {url}: {e}")
        return False


async def get_store_public_info(url: str) -> Dict[str, Any]:
    """
    Fetches comprehensive public information about the store from its homepage.
    Extracts store name, description, social media links, contact info, branding elements,
    and other relevant metadata.
    """
    info: Dict[str, Any] = {
        "name": None,
        "description": None,
        "favicon": None,
        "url": url,
        "tag": "Website",
        "metadata": {
            "keywords": [],
            "robots": None,
            "viewport": None,
            "charset": None
        },
        "social_media": {},
        "contact_info": {
            "email": None,
            "phone": None,
            "address": None
        },
        "branding": {
            "logo": None,
            "colors": [],
            "fonts": []
        },
        "navigation": {
            "main_menu": [],
            "footer_links": []
        },
        "store_features": [],
        "language": None,
        "currency": None
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, follow_redirects=True, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Get store name from title tag
            if soup.title and soup.title.string:
                info["name"] = soup.title.string.strip()

            # Get meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc and meta_desc.get('content'):
                info["description"] = meta_desc['content'].strip()

            # Get meta keywords
            meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
            if meta_keywords and meta_keywords.get('content'):
                info["metadata"]["keywords"] = [
                    k.strip() for k in meta_keywords['content'].split(',')
                ]

            # Get other meta tags
            meta_robots = soup.find('meta', attrs={'name': 'robots'})
            if meta_robots and meta_robots.get('content'):
                info["metadata"]["robots"] = meta_robots['content']

            meta_viewport = soup.find('meta', attrs={'name': 'viewport'})
            if meta_viewport and meta_viewport.get('content'):
                info["metadata"]["viewport"] = meta_viewport['content']

            meta_charset = soup.find('meta', attrs={'charset': True})
            if meta_charset:
                info["metadata"]["charset"] = meta_charset['charset']

            # Get favicon URL
            icon_link = soup.find(
                'link', rel=['icon', 'shortcut icon', 'apple-touch-icon'])

            if isinstance(icon_link, Tag) and icon_link.get('href'):
                favicon_url_relative = icon_link.get('href')
                # Make sure the favicon URL is absolute
                if favicon_url_relative and not favicon_url_relative.startswith('http'):
                    # Attempt to construct absolute URL
                    favicon_url = urljoin(url, favicon_url_relative)
                else:
                    favicon_url = favicon_url_relative
                info["favicon"] = favicon_url

            # Get social media links
            social_platforms = {
                'facebook': ['facebook.com', 'fb.com'],
                'instagram': ['instagram.com'],
                'twitter': ['twitter.com', 'x.com'],
                'pinterest': ['pinterest.com'],
                'youtube': ['youtube.com'],
                'linkedin': ['linkedin.com'],
                'tiktok': ['tiktok.com']
            }

            for platform, domains in social_platforms.items():
                social_link = soup.find('a', href=lambda x: x and any(
                    domain in x.lower() for domain in domains))
                if social_link and social_link.get('href'):
                    info["social_media"][platform] = social_link['href']

            # Get contact information
            # Email
            email_links = soup.find_all(
                'a', href=lambda x: x and x.startswith('mailto:'))
            if email_links:
                info["contact_info"]["email"] = email_links[0]['href'].replace(
                    'mailto:', '')

            # Phone
            phone_links = soup.find_all(
                'a', href=lambda x: x and x.startswith('tel:'))
            if phone_links:
                info["contact_info"]["phone"] = phone_links[0]['href'].replace(
                    'tel:', '')

            # Address (look for common address patterns in text)
            address_patterns = [
                r'\d+\s+[A-Za-z\s,]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Circle|Cir|Way|Place|Pl)[,\s]+[A-Za-z\s]+,\s*[A-Z]{2}\s*\d{5}',
                r'\d+\s+[A-Za-z\s,]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Circle|Cir|Way|Place|Pl)[,\s]+[A-Za-z\s]+,\s*[A-Za-z\s]+,\s*[A-Z]{2}\s*\d{5}'
            ]

            for pattern in address_patterns:
                address_match = re.search(pattern, response.text)
                if address_match:
                    info["contact_info"]["address"] = address_match.group(0)
                    break

            # Get branding elements
            # Logo
            logo_img = soup.find('img', attrs={'class': lambda x: x and any(
                term in x.lower() for term in ['logo', 'brand'])})
            if logo_img and logo_img.get('src'):
                logo_src = logo_img['src']
                if not logo_src.startswith('http'):
                    logo_src = urljoin(url, logo_src)
                info["branding"]["logo"] = logo_src

            # Get main navigation menu items
            nav_links = soup.find_all('a', attrs={'class': lambda x: x and any(
                term in x.lower() for term in ['nav', 'menu', 'header'])})
            for link in nav_links:
                if link.text.strip():
                    info["navigation"]["main_menu"].append({
                        "text": link.text.strip(),
                        "url": urljoin(url, link.get('href', ''))
                    })

            # Get footer links
            footer_links = soup.find_all('a', attrs={'class': lambda x: x and any(
                term in x.lower() for term in ['footer', 'bottom'])})
            for link in footer_links:
                if link.text.strip():
                    info["navigation"]["footer_links"].append({
                        "text": link.text.strip(),
                        "url": urljoin(url, link.get('href', ''))
                    })

            # Get store features from meta tags and structured data
            feature_tags = soup.find_all(
                'meta', attrs={'property': lambda x: x and 'product:' in x})
            for tag in feature_tags:
                if tag.get('content'):
                    info["store_features"].append(tag['content'])

            # Get language and currency from meta tags
            lang_tag = soup.find('html', attrs={'lang': True})
            if lang_tag:
                info["language"] = lang_tag['lang']

            # Look for currency in meta tags or structured data
            currency_tag = soup.find(
                'meta', attrs={'property': 'product:price:currency'})
            if currency_tag and currency_tag.get('content'):
                info["currency"] = currency_tag['content']

    except httpx.RequestError as e:
        logger.warning(
            f"Could not fetch store info from {url} via HTTP request: {e}")
    except Exception as e:
        logger.warning(
            f"An unexpected error occurred during store info gathering for {url}: {e}")

    return info
