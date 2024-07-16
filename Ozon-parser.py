import time
import json

from selenium import webdriver
from selenium_stealth import stealth
from bs4 import BeautifulSoup

from curl_cffi import requests

def init_webdriver():
    driver = webdriver.Chrome()
    stealth(driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True)
    driver.maximize_window()
    return driver

def scrolldown(driver, deep):
    for _ in range(deep):
        driver.execute_script('window.scrollBy(0, 500)')
        time.sleep(0.1)

def get_product_info(product_url):
    session = requests.Session()

    raw_data = session.get("https://www.ozon.ru/api/composer-api.bx/page/json/v2?url=" + product_url)
    json_data = json.loads(raw_data.content.decode())

    full_name = json_data["seo"]["title"]

    if json_data["layout"][0]["component"] == "userAdultModal":
        product_id = str(full_name.split()[-1])[1:-1]
        print(product_id, full_name)
        return (product_id, full_name, "Товар для лиц старше 18 лет", None, None)
    else:
        description = json.loads(json_data["seo"]["script"][0]["innerHTML"])["description"]
        image_url = json.loads(json_data["seo"]["script"][0]["innerHTML"])["image"]
        price = json.loads(json_data["seo"]["script"][0]["innerHTML"])["offers"]["price"] + " " +\
                json.loads(json_data["seo"]["script"][0]["innerHTML"])["offers"]["priceCurrency"]
        rating = json.loads(json_data["seo"]["script"][0]["innerHTML"]["ratingValue"])
        rating_counter = json.loads(json_data["seo"]["script"][0]["innerHTML"]["reviewCount"])
        product_id = json.loads(json_data["seo"]["script"][0]["innerHTML"])["sku"]

        return (product_id, full_name, description, price, rating, rating_counter, image_url)

def get_mainpage_cards(driver, url):
    driver.get(url)
    scrolldown(driver, 50)
    main_page_html = BeautifulSoup(driver.page_source, "html.parser")

    content = main_page_html.find("div", {"class": "container"})
    content = content.findChildren(recursive=False)[-1].find("div")
    content = content.findChildren(recursive=False)
    content = [item for item in content if "freshIsland" in str(item)][-1]
    content = content.find("div").find("div").find("div")
    content = content.findChildren(recursive=False)

    all_cards = list()
    for layer in content:
        layer = layer.find("div")
        cards = layer.findChildren(recursive=False)

        cards_in_layer = list()
        for card in cards:
            card = card.findChildren(recursive=False)

            card_name = card[2].find("span", {"class": "tsBody500Medium"}).contents[0]
            card_url = card[2].find("a", href=True)["href"]
            product_url = "https://ozon.ru/" + card_url

            product_id, full_name, description, price, rating, rating_counter, image_url = get_product_info(card_url)
            card_info = {product_id: {"short_name": card_name,
                                      "full_name": full_name,
                                      "description": description,
                                      "url": product_url,
                                      "rating": rating,
                                      "rating_counter": rating_counter,
                                      "price": price,
                                      "image_url": image_url
                                      }
                         }
            cards_in_layer.append(card_info)
            print(product_id, "- DONE")

        all_cards.extend(cards_in_layer)
    return all_cards

def get_searchpage_cards(driver, url, all_cards = []):
    driver.get(url)
    scrolldown(driver, 20)
    search_page_html = BeautifulSoup(driver.page_source, "html.parser")

    content = search_page_html.find("div", {"id": "layoutPage"})
    content = content.find("div")

    content_with_cards = content.find("div", {"class": "widget-search-result-container"})
    content_with_cards = content_with_cards.find("div").findChildren(recursive=False)

    cards_in_page = list()
    for card in content_with_cards:
        card_url = card.find("a", href=True)["href"]
        card_name = card.find("span", {"class": "tsBody500Medium"}).contents[0]

        product_url = "https://ozon.ru/" + card_url

        product_id, full_name, description, price, rating, rating_counter, image_url = get_product_info(card_url)
        card_info = {product_id: {"short_name": card_name,
                                  "full_name": full_name,
                                  "description": description,
                                  "url": product_url,
                                  "rating": rating,
                                  "rating_counter": rating_counter,
                                  "price": price,
                                  "image_url": image_url
                                  }
                     }
        cards_in_page.append(card_info)
        print(product_id, "- DONE")

    content_with_next = [div for div in content.find_all("a", href=True) if "Дальше" in str(div)]
    if not content_with_next:
        return cards_in_page
    else:
        next_page_url = "https://www.ozon.ru" + content_with_next[0]["href"]
        all_cards.extend(get_searchpage_cards(driver, next_page_url, cards_in_page))
        return all_cards


if __name__ == "__main__":
    url_ozon = "https://www.ozon.ru"

    driver = init_webdriver()

    search_list = ["пиво+светлое", "бандана+мужская+с+черепами", "сухарики+кириешки", "RTX+4090"]
    end_list = list()

    try:
        main_cards = get_mainpage_cards(driver, url_ozon)
        print("Я успешно нашёл", len(main_cards), "на главной странице")
        end_list.append("MAIN")
    except:
        print("Я упал на парсинге главной страницы")

    for search_tag in search_list:
        url_search = f"https://www.ozon.ru/search/?text={search_tag}&from_global=true"

        try:
            search_cards = get_searchpage_cards(driver, url_search)
            print("Я успешно нашёл", len(search_cards), "по поиску", search_tag)
            end_list.append(search_tag)
        except:
            print("Я упал на", search_tag)
    print(end_list)

    driver.quit()
