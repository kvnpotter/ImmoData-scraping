# Imports

from multiprocessing import get_context, cpu_count, Pool
import json
from GetListingURLs import quick_get_urls
from ScrapeListings import quick_parse

# Functions

def get_dict_from_url(url: str, headers: dict[str:str], session: Session, line_number: int) -> dict:

    soup = get_soup(url, headers, session, line_number)

    # Parse the content to find the <script> tag containing "window.classified"
    script_tag = soup.find('script', string=re.compile(r'window\.classified\s*='))

    if script_tag:
        print(f"Got script_tag for {url}")
        # Extract the JSON part from the script content
        match = re.search(r'window\.classified\s*=\s*(\{.*?\});', script_tag.string)
        if match:
            classified_data = match.group(1)
            # Parse the JSON data
            classified_dict = json.loads(classified_data)

            return classified_dict

        else:
            print(f"JSON data not found within the script tag for {url}.")
    else:
        print(f"Script tag with 'window.classified' not found for {url}.")


def read_parse_listings(url_list: list[str],
                        index_range,
                        headers: dict[str:str] = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',},
                        session: Session = requests.Session()) -> list[dict]:

    result = []
    individual_urls = []

    for line_number in index_range:
        url = url_list[line_number].strip()

        listing_dict = get_dict_from_url(url, headers, session, line_number)

        if is_compound_sale(listing_dict):
            print(f"Solving compound listing for {url}")
            soup = get_soup(url, headers, session, None)
            individual_listings = get_compound_sale_urls(soup)
            for listing_url in individual_listings:
                individual_urls.append(listing_url)
                individual_dict = get_dict_from_url(listing_url, headers, session, None)
                result.append(individual_dict)

        else:
            individual_urls.append(url)
            result.append(listing_dict)

    return result, individual_urls

def quick_parse(url_list: list[str], num_processes: int = None) -> list[dict]:

    if num_processes is None:
        num_processes = cpu_count()  # Use the number of available CPUs by default
    
    """
    Function allowing to perform parsing with get_relevant_info using multiprocessing.

    : param list_dicts_listings: list: List of dictionaries containing ImmoWeb listing information for each property.
    : param num_processes: int: Number of processes to use in multiprocessing.

    : return: list: List of dicts with required information.
    """

    if num_processes is None:
        num_processes = cpu_count()  # Use the number of available CPUs by default

    dict_index_ranges = [range(i, len(list_dicts_listings), num_processes) for i in range(num_processes)]

    relevant_dicts = []

    with get_context('spawn').Pool(processes=num_processes) as pool:
        results = pool.starmap(get_relevant_info, [(list_dicts_listings, dict_index_range) for dict_index_range in dict_index_ranges])

        for result in results:
            relevant_dicts.extend(result)
            
    return relevant_dicts

def get_relevant_info(list_dicts_listings: list[dict],
                      dict_index_range) -> list[dict]:
    
    """
    Function to extract required information from listing dictionaries.

    : param list_dicts_listings: list: List of dictionaries containing ImmoWeb listing information for each property.
    : param dict_index_range: range: Range of dictionaries to handle from the list, for multiprocessing.

    : return: List of dicts containing required information.
    """
    
    # List will contain dictionaries for each listing containing relevant info
    relevant_info_list = []
    
    # Iterate over each listing in the main dictionary.
    for i in dict_index_range:

        print(f"Parsing listing dict {i}")
        
        listing = list_dicts_listings[i]

        id = None 
        id = listing.get('id')

        locality = None
        locality = listing.get('property', {}).get('location', {}).get('postalCode')

        property_type = None
        property_type = listing.get('property', {}).get('type')

        property_subtype = None
        property_subtype = listing.get('property', {}).get('subtype')

        price = None
        price = listing.get('transaction', {}).get('sale', {}).get('price')

        sale_type = None
        sale_type = listing.get('price', {}).get('type')

        rooms = None
        rooms = listing.get('property', {}).get('bedroomCount')

        living_area = None
        living_area = listing.get('property', {}).get('netHabitableSurface')

        # Need to make sure what the different status posibilies are
        is_kitchen_equipped = None
        if listing.get('property', {}).get('kitchen', {}) != None:
            kitchen_equipped_status = listing.get('property', {}).get('kitchen', {}).get('type')
            if kitchen_equipped_status is not None and kitchen_equipped_status != "None" and kitchen_equipped_status != "":
                kitchen_equipped_status = kitchen_equipped_status.lower()
                if kitchen_equipped_status in ["uninstalled", "usa uninstalled"]:
                    is_kitchen_equipped = 0
                else:
                    is_kitchen_equipped = 1
        else:
            is_kitchen_equipped = None

        # Need to double check status possibilities
        is_furnished = None
        furnished_status = listing.get('transaction', {}).get('sale', {}).get('isFurnished')
        if furnished_status:
            is_furnished = 1
        elif furnished_status == None:
            is_furnished = None
        else:
            is_furnished = 0

        is_fireplace = None
        fireplace_status = listing.get('property', {}).get('fireplaceExists')
        if fireplace_status is not None and fireplace_status != "None" and fireplace_status != "":
            if fireplace_status == True:
                is_fireplace = 1
            else:
                is_fireplace = 0

        is_terrace = None
        terrace_status = listing.get('property', {}).get('hasTerrace')
        if terrace_status is not None and terrace_status != "None" and terrace_status != "":
            if terrace_status == True:
                is_terrace = 1
            else: 
                is_terrace = 0

        terrace_area = None
        terrace_area = listing.get('property', {}).get('terraceSurface')

        is_garden = None
        garden_status = listing.get('property', {}).get('hasGarden')
        if garden_status is not None and garden_status != "None" and garden_status != "":
            if garden_status == True:
                is_garden = 1
            else:
                is_garden = 0

        garden_area = None
        garden_area = listing.get('property', {}).get('gardenSurface')

        # Garden area twice??
        surface_land = None
        surface_land = listing.get('property', {}).get('gardenSurface')

        #surface_land + living area
        surface_area_plot = None
        if listing.get('property', {}).get('land', {}) != None:
            surface_area_plot = listing.get('property', {}).get('land', {}).get('surface')
        else:
           surface_area_plot = None 

        facades = None
        if listing.get('property', {}).get('building', {}) != None:
            facades = listing.get('property', {}).get('building', {}).get('facadeCount')
        else:
            facades = None

        is_pool = None
        pool_status = listing.get('property', {}).get('hasSwimmingPool')
        if pool_status is not None and pool_status != "None" and pool_status != "":
            if pool_status == True:
                is_pool = 1
            else:
                is_pool = 0

        building_state = None
        if listing.get('property', {}).get('building', {}) != None:
            building_state = listing.get('property', {}).get('building', {}).get('condition')
        else:
           building_state = None 

        #Extract info from listings into a dictionary
        relevant_info = {'id': id,
                         'Locality': locality,
                         'Type of property': property_type,
                         'Subtype of property': property_subtype,
                         'Price': price,
                         'Type of sale': sale_type,
                         'Number of rooms': rooms,
                         'Living Area': living_area,
                         'Fully equipped kitchen': is_kitchen_equipped,
                         'Furnished': is_furnished,
                         'Fireplace': is_fireplace,
                         'Terrace': is_terrace,
                         'Terrace area': terrace_area,
                         'Garden': is_garden,
                         'Garden area': garden_area,
                         'Surface of the land': surface_land,
                         'Surface area of the plot of land': surface_area_plot,
                         'Number of facades': facades,
                         'Swimming pool': is_pool,
                         'State of the building': building_state
                        }

        # Add dictionary for listing to our list.
        relevant_info_list.append(relevant_info)

<<<<<<< HEAD
<<<<<<< HEAD:GetListingDetails.py
    return relevant_info_list

def is_compound_sale(classified_dict: dict) -> bool:
    return classified_dict['cluster'] != None

def get_compound_sale_urls(soup: BeautifulSoup) -> list[str]:
    individual_urls = []
    
    # Find all tags that include the text 'apartment'
    tags_with_text = soup.find_all(string=lambda text: "apartment" in text.lower())
    
    # Check each tag for a parent with the class 'grid'
    for tag in tags_with_text:
        # Find the closest parent 'div' with class 'grid'
        grid = tag.find_parent('div', class_='grid')
        if grid:
            # Now, check for subtitles and extract valid links
            subtitles = grid.find_all('span', class_='text-block__subtitle')
            
            # We already know this grid contains an "apartment" mention
            links = grid.find_all('a', href=True)
            valid_links = [link['href'] for link in links if link['href'].startswith("https://www.immoweb.be/en/classified/")]

            # Extend individual_urls with valid links if found
            if valid_links:
                individual_urls.extend(valid_links)
                # Optionally print each found URL
                #for valid_link in valid_links:
                    #print(f"Found URL: {valid_link}")

    return individual_urls


if __name__ == "__main__":

    number_pages = 2
    start_time_multi = perf_counter()

    list = quick_get_urls(number_pages)
    dicts = quick_parse(list)
    relevant = quick_relevant(dicts)
    print(len(relevant))
    print(relevant[0])
    print(relevant[-1])
    print(f"\nTime spent inside the multi loop: {perf_counter() - start_time_multi} seconds.")  
=======
    return relevant_info_list
>>>>>>> 1b01d66 (Major restructuring and combining of code):ImmoWebScraper/ImmoWebScraper/ParseListingDict.py
=======
    return relevant_info_list

if __name__ == "__main__":

    with open("list_of_dicts.json", "r") as file:
        listing_dicts = json.load(file)

    relevant_info = quick_relevant(listing_dicts)

    print(f"Number of relevant info dicts created {len(relevant_info)}")
    print(relevant_info[-1])

    with open("./ImmoWebScraper/Data/relevant_dicts.json", "w+") as file:
        json.dump(relevant_info, file)
>>>>>>> e8c431b (Working Scraper and Data created)
