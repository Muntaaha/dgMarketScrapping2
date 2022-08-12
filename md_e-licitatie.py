import logging
import re
import time
from datetime import date, datetime, timedelta
import dateparser
from deep_translator import GoogleTranslator
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
from selenium.webdriver.common.by import By
import common.OutputXML
import functions as fn
from common.NoticeData import NoticeData

MAX_NOTICES = 2000
SCRIPT_NAME = "md_e-licitatie"
notice_count = 0
output_xml_file = common.OutputXML.OutputXML(SCRIPT_NAME)

def extract_and_save_notice(tender_html_element):
    global notice_count
    global notice_data
    notice_data = NoticeData()
    notice_data.procurement_method = "Other"
    notice_data.language = "RO"
    notice_data.notice_type = 'spn'
    notice_data.performance_country = "Moldova"
    notice_data.contact_country = "Moldova"

    try:
        notice_data.title_en = page_main.find_element(By.XPATH, '/html/body/div[2]/div[2]/div[2]/div[1]/div/div[2]/div/div[2]/div['+str(tender_html_element)+']/div/div[2]/div[1]/h3/a').text.strip()
        notice_data.title_en = GoogleTranslator(source='auto', target='en').translate(notice_data.title_en)
    except:
        pass

    try:
        notice_data.buyer = page_main.find_element(By.XPATH, '/html/body/div[2]/div[2]/div[2]/div[1]/div/div[2]/div/div[2]/div['+str(tender_html_element)+']/div/div[2]/div[3]/div[2]/a').text.strip()
    except:
        pass

    try:
        EOS = page_main.find_element(By.XPATH,'/html/body/div[2]/div[2]/div[2]/div[1]/div/div[2]/div/div[2]/div['+str(tender_html_element)+']/div/div[2]/div[2]/p').text
        notice_data.est_cost = re.sub("[^\d\.]", "", EOS)
        notice_data.currency = "MDL"
    except:
        pass

    try:
        notice_data.notice_url = page_main.find_element(By.XPATH, '/html/body/div[2]/div[2]/div[2]/div[1]/div/div[2]/div/div[2]/div['+str(tender_html_element)+']/div/div[2]/div[1]/h3/a').get_attribute('href')
        fn.load_page(page_details, notice_data.notice_url)

        try:
            notice_data.notice_text += wait_detail.until(EC.presence_of_element_located((By.XPATH,'/html/body/div[2]/div[2]/div/div'))).get_attribute('outerHTML')
        except:
            pass

        try:
            notice_data.published_date = page_details.find_element(By.XPATH, '/html/body/div[2]/div[2]/div/div/div[2]/div[2]/div[2]/div[5]/div[1]/div[2]/strong').text
            notice_data.published_date = re.findall('\d+/\d+/\d{4}', notice_data.published_date)[0]
            notice_data.published_date = datetime.strptime(notice_data.published_date, '%d/%m/%Y').strftime('%Y/%m/%d')
        except:
            pass

        if notice_data.published_date is not None and notice_data.published_date < threshold:
            return

        try:
            notice_data.end_date = page_details.find_element(By.XPATH, '/html/body/div[2]/div[2]/div/div/div[2]/div[2]/div[2]/div[5]/div[3]/div[2]/strong').text
            notice_data.end_date = re.findall('\d+/\d+/\d{4}', notice_data.end_date)[0]
            notice_data.end_date = datetime.strptime(notice_data.end_date, '%d/%m/%Y').strftime('%Y/%m/%d')
        except:
            pass

        try:
            notice_data.resource_url = []
            resources = page_details.find_element(By.XPATH,'/html/body/div[2]/div[2]/div/div/div[2]/div[5]/div[2]/div/div[2]/table/tbody').find_elements(By.CSS_SELECTOR, 'tr')
            for each_resource in resources:
                resource_url = each_resource.find_element(By.CSS_SELECTOR,'td:nth-of-type(6) a').get_attribute('href')
                notice_data.resource_url.append(resource_url)
        except:
            pass

        try:
            notice_data.contact_name = page_details.find_element(By.XPATH, '/html/body/div[2]/div[2]/div/div/div[2]/div[6]/div[2]/div/div[1]/input').get_attribute('value')
        except:
            pass

        try:
            notice_data.contact_email = page_details.find_element(By.XPATH, '/html/body/div[2]/div[2]/div/div/div[2]/div[6]/div[2]/div/div[2]/input').get_attribute('value')
        except:
            pass

        try:
            notice_data.contact_phone = page_details.find_element(By.XPATH, '/html/body/div[2]/div[2]/div/div/div[2]/div[6]/div[2]/div/div[3]/input').get_attribute('value')
        except:
            pass

    except:
        notice_data.notice_url = url

    notice_data.cleanup()
    logging.info('-------------------------------')
    output_xml_file.writeNoticeToXMLFile(notice_data)
    notice_count += 1

# ----------------------------------------- Main Body
page_main = fn.init_chrome_driver()
page_details = fn.init_chrome_driver()
wait = WebDriverWait(page_main, 20)
wait_detail = WebDriverWait(page_details, 20)
try:
    th = date.today() - timedelta(1)
    threshold = th.strftime('%Y/%m/%d')
    logging.info("Scraping from or greater than: " + threshold)
    url = 'https://e-licitatie.md/'
    logging.info('----------------------------------')
    fn.load_page(page_main, url)
    logging.info(url)
    for page_number in range(2,11):
        page_check = WebDriverWait(page_main, 120).until(EC.presence_of_element_located((By.XPATH,'/html/body/div[2]/div[2]/div[2]/div[1]/div/div[2]/div/div[2]/div[1]/div/div[2]/div[1]/h3/a'))).text
        for tender_html_element in range(1,11):
            extract_and_save_notice(tender_html_element)
            if notice_count >= MAX_NOTICES:
                break

            if notice_data.published_date is not None and  notice_data.published_date < threshold:
                break

        try:
            url = 'https://e-licitatie.md/?page='+str(page_number)+'&per-page=10'
            fn.load_page(page_main, url)
            WebDriverWait(page_main, 50).until_not(EC.text_to_be_present_in_element((By.XPATH,'/html/body/div[2]/div[2]/div[2]/div[1]/div/div[2]/div/div[2]/div[1]/div/div[2]/div[1]/h3/a'),page_check))
            logging.info("Next Page")
        except:
            logging.info("No Next Page")
            break


    logging.info("Finished processing. Scraped {} notices".format(notice_count))
    fn.session_log(SCRIPT_NAME, notice_count, 'XML uploaded')
except Exception as e:
    try:
        fn.error_log(SCRIPT_NAME, e)
        fn.session_log(SCRIPT_NAME, notice_count, 'Script error')
    except:
        pass
    raise e
finally:
    logging.info('finally')
    page_main.quit()
    page_details.quit()
    output_xml_file.copyFinalXMLToServer("europe")

