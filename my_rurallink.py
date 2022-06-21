import logging
import re
import time
from datetime import date, datetime, timedelta
from selenium.webdriver.support.select import Select

import ml.cpv_classifier as classifier
from false_cpv import false_cpv

from deep_translator import GoogleTranslator
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

import common.OutputXML
import functions as fn
from common.NoticeData import NoticeData

MAX_NOTICES = 2000

ml_cpv = 0
notice_count = 0
output_xml_file = common.OutputXML.OutputXML("my_rurallink")


def extract_and_save_notice(tender_html_element):
    global ml_cpv
    global notice_count

    notice_data = NoticeData()

    notice_data.performance_country = 'Malaysia'
    notice_data.contact_country = 'Malaysia'
    notice_data.address = 't will be static "No. 47, Persiaran Perdana, Precinct 4, Federal Government Administrative Center, 62100 Putrajaya, Malaysia.'
    notice_data.contact_phone = '03 8000 8000'
    notice_data.contact_email = 'info@rurallink.gov.my'
    notice_data.procurement_method = "Other"
    notice_data.language = "EN"

    try:
        notice_data.reference = tender_html_element.find_element(By.CSS_SELECTOR, 'td:nth-of-type(3)').text.split("\n")[1]
        logging.info(notice_data.reference)
    except:
        notice_data.reference = ''

    notice_data.buyer = 'Ministry of Rural Development'
    notice_data.buyer_internal_id = 'Ministry of Rural Development'

    try:
        notice_data.title_en = tender_html_element.find_element(By.CSS_SELECTOR, 'td:nth-of-type(2)').text.split('\n')[0]
        notice_data.title_en = GoogleTranslator(source='auto', target='en').translate(notice_data.title_en)
    except:
        notice_data.title_en = ''

    try:
        notice_data.published_date = tender_html_element.find_element(By.CSS_SELECTOR, 'td:nth-of-type(5)').text
        notice_data.published_date = re.findall('\d+/\d+/\d{4}', notice_data.published_date)[0]
        notice_data.published_date = datetime.strptime(notice_data.published_date, '%d/%m/%Y').strftime('%Y/%m/%d')
    except:
        return

    try:
        notice_data.end_date = tender_html_element.find_element(By.CSS_SELECTOR, 'td:nth-of-type(6)').text
        notice_data.end_date = re.findall('\d+/\d+/\d{4}', notice_data.end_date)[0]
        notice_data.end_date = datetime.strptime(notice_data.end_date, '%d/%m/%Y').strftime('%Y/%m/%d')
    except:
        return

    if notice_data.published_date < threshold:
        return

    notice_data.notice_type = 'spn'

    notice_data.organization_name = notice_data.buyer

    rsrs = tender_html_element.find_element(By.CSS_SELECTOR, 'td:nth-of-type(6)').get_attribute('href')

    notice_data.notice_text += notice_data.buyer + ' has invited a tender.'
    notice_data.notice_text += '</br>'
    notice_data.notice_text += 'Reference No: '
    notice_data.notice_text += notice_data.reference
    notice_data.notice_text += '</br>'
    notice_data.notice_text += notice_data.title_en
    notice_data.notice_text += '</br>'
    notice_data.notice_text += 'Published Date : '
    notice_data.notice_text += notice_data.published_date
    notice_data.notice_text += '</br>'
    notice_data.notice_text += 'End date : '
    notice_data.notice_text += notice_data.end_date
    notice_data.notice_text += '</br></br>'

    cpvs = classifier.get_cpvs(notice_data.title_en.lower(), notice_data.category)
    cpv_count = 0
    if cpvs:
        for cpv in cpvs:
            if cpv not in false_cpv:
                notice_data.cpvs.append(cpv)
                cpv_count += 1
    if cpv_count != 0:
        ml_cpv += 1

    output_xml_file.writeNoticeToXMLFile(notice_data)
    notice_count += 1

# ----------------------------------------- Main Body

chrome_options = Options()
chrome_options.add_argument("--headless")
page_main = webdriver.Chrome(options=chrome_options)
page_details = webdriver.Chrome(options=chrome_options)
profile = webdriver.FirefoxProfile()

# try:
#     page_main = webdriver.Firefox(executable_path='/home/dgmarket/Documents/scraps/geckodriver-v0.24.0-linux64/geckodriver', firefox_profile=profile)
#     page_details = webdriver.Firefox(executable_path='/home/dgmarket/Documents/scraps/geckodriver-v0.24.0-linux64/geckodriver', firefox_profile=profile)
# except: 
#     time.sleep(15)
#     page_main = webdriver.Firefox(executable_path='/home/dgmarket/Documents/scraps/geckodriver-v0.24.0-linux64/geckodriver', firefox_profile=profile)
#     page_details = webdriver.Firefox(executable_path='/home/dgmarket/Documents/scraps/geckodriver-v0.24.0-linux64/geckodriver', firefox_profile=profile)


try:
    days = fn.last_success('my_rurallink') + 1
    th = date.today() - timedelta(days)
    threshold = th.strftime('%Y/%m/%d')
    logging.info("Scraping from or greater than: " + threshold)

    url = 'https://www.rurallink.gov.my/tender-sebut-harga/iklan-tawaran-tender/'
    logging.info('----------------------------------')
    logging.info(url)
    page_main.get(url)
    time.sleep(5)

    total_pages = page_main.find_element(By.XPATH, '/html/body/div[1]/div/main/div[1]/div/div/section[4]/div/div/div/div/div/div/div/div/div/div[2]/div[5]').text
    total_pages = total_pages.split(' ')[5].strip()
    total_pages = total_pages.replace(',','').strip()
    total_pages = int(total_pages) // 10
    print(total_pages+1)
    for i in range(total_pages+1):
        for tender_html_element in page_main.find_element(By.XPATH, '/html/body/div[1]/div/main/div[1]/div/div/section[4]/div/div/div/div/div/div/div/div/div/div[2]/table/tbody').find_elements(By.CSS_SELECTOR, 'tr'):
            extract_and_save_notice(tender_html_element)
            if notice_count >= MAX_NOTICES:
                break
        try:
            next_page = page_main.find_element(By.XPATH, '//*[@id="table_1_next"]')
            page_main.execute_script("arguments[0].click();", next_page)
            time.sleep(5)
        except:
            break

    url = 'https://www.rurallink.gov.my/tender-sebut-harga/iklan-kenyataan-tender-perunding/'
    logging.info('----------------------------------')
    logging.info(url)
    page_main.get(url)
    time.sleep(5)

    total_pages = page_main.find_element(By.XPATH, '/html/body/div[1]/div/main/div[1]/div/div/section[4]/div/div/div/div/div/div/div/div/div/div[2]/div[5]').text
    total_pages = total_pages.split(' ')[5].strip()
    total_pages = total_pages.replace(',','').strip()
    total_pages = int(total_pages) // 10
    print(total_pages+1)
    for i in range(total_pages+1):
        for tender_html_element in page_main.find_element(By.XPATH, '/html/body/div[1]/div/main/div[1]/div/div/section[4]/div/div/div/div/div/div/div/div/div/div[2]/table/tbody').find_elements(By.CSS_SELECTOR, 'tr'):
            extract_and_save_notice(tender_html_element)
            if notice_count >= MAX_NOTICES:
                break
        try:
            next_page = page_main.find_element(By.XPATH, '//*[@id="table_1_next"]')
            page_main.execute_script("arguments[0].click();", next_page)
            time.sleep(5)
        except:
            break

    url = 'https://www.rurallink.gov.my/tender-sebut-harga/iklan-kenyataan-sebutharga/'
    logging.info('----------------------------------')
    logging.info(url)
    page_main.get(url)
    time.sleep(5)

    total_pages = page_main.find_element(By.XPATH, '/html/body/div[1]/div/main/div[1]/div/div/section[4]/div/div/div/div/div/div/div/div/div/div[2]/div[5]').text
    total_pages = total_pages.split(' ')[5].strip()
    total_pages = total_pages.replace(',','').strip()
    total_pages = int(total_pages) // 10
    print(total_pages+1)
    for i in range(total_pages+1):
        for tender_html_element in page_main.find_element(By.XPATH, '/html/body/div[1]/div/main/div[1]/div/div/section[4]/div/div/div/div/div/div/div/div/div/div[2]/table/tbody').find_elements(By.CSS_SELECTOR, 'tr'):
            extract_and_save_notice(tender_html_element)
            if notice_count >= MAX_NOTICES:
                break
        try:
            next_page = page_main.find_element(By.XPATH, '//*[@id="table_1_next"]')
            page_main.execute_script("arguments[0].click();", next_page)
            time.sleep(5)
        except:
            break

    url = 'https://www.rurallink.gov.my/tender-sebut-harga/iklan-kenyataan-kerja-undi/'
    logging.info('----------------------------------')
    logging.info(url)
    page_main.get(url)
    time.sleep(5)

    total_pages = page_main.find_element(By.XPATH, '/html/body/div[1]/div/main/div[1]/div/div/section[4]/div/div/div/div/div/div/div/div/div/div[2]/div[5]').text
    total_pages = total_pages.split(' ')[5].strip()
    total_pages = total_pages.replace(',','').strip()
    total_pages = int(total_pages) // 10
    print(total_pages+1)
    for i in range(total_pages+1):
        for tender_html_element in page_main.find_element(By.XPATH, '/html/body/div[1]/div/main/div[1]/div/div/section[4]/div/div/div/div/div/div/div/div/div/div[2]/table/tbody').find_elements(By.CSS_SELECTOR, 'tr'):
            extract_and_save_notice(tender_html_element)
            if notice_count >= MAX_NOTICES:
                break
        try:
            next_page = page_main.find_element(By.XPATH, '//*[@id="table_1_next"]')
            page_main.execute_script("arguments[0].click();", next_page)
            time.sleep(5)
        except:
            break

    logging.info("Finished processing. Scraped {} notices".format(notice_count))
    fn.session_log('my_rurallink', notice_count, 0, ml_cpv, 'XML uploaded')

except Exception as e:
    try:
        fn.error_log('my_rurallink', e)
        fn.session_log('my_rurallink', notice_count, 0, ml_cpv, 'Script error')
    except:
        pass
    raise e
finally:
    page_main.quit()
    page_details.quit()
    output_xml_file.copyFinalXMLToServer("asia")
