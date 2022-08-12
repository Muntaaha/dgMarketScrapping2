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
SCRIPT_NAME = "tn_ommp"
notice_count = 0
output_xml_file = common.OutputXML.OutputXML(SCRIPT_NAME)

def extract_and_save_notice(tender_html_element):
    global notice_count
    global notice_data
    notice_data = NoticeData()
    notice_data.performance_country = 'Tunisia'
    notice_data.contact_country = 'Tunisia'
    notice_data.procurement_method = "Other"
    notice_data.language = "FR"
    notice_data.notice_type = 'spn'
    notice_data.buyer = 'OFFICE DE LA MARINE MARCHANDE ET DES PORTS'
    notice_data.buyer_internal_id = '7680460'

    try:
        notice_data.reference = tender_html_element.find_element(By.CSS_SELECTOR, '.entry-header h2 a').text
        try:
            notice_data.reference = 'N°'+ notice_data.reference.split("N°")[2].strip()
        except:
            notice_data.reference = 'N°'+ notice_data.reference.split("N°")[1].strip()
    except:
        pass

    try:
        notice_data.title_en = tender_html_element.find_element(By.CSS_SELECTOR, '.entry-content h5').text.strip()
        notice_data.title_en = GoogleTranslator(source='auto', target='en').translate(notice_data.title_en)
    except:
        pass

    try:
        notice_data.end_date = tender_html_element.find_element(By.CSS_SELECTOR, '.entry-content').text
        notice_data.end_date = re.findall('\d+ \w+ \d{4}', notice_data.end_date)[0]
        notice_data.end_date = dateparser.parse(notice_data.end_date, settings={'DATE_ORDER': 'DMY'})
        notice_data.end_date = str(notice_data.end_date)
        notice_data.end_date = datetime.strptime(notice_data.end_date, '%Y-%m-%d %X').strftime('%Y/%m/%d')
    except:
        notice_data.end_date = ''

    try:
        notice_data.notice_url = tender_html_element.find_element(By.CSS_SELECTOR, '.entry-header h2 a').get_attribute('href')
        fn.load_page(page_details, notice_data.notice_url)

        try:
            notice_data.notice_text += wait_detail.until(EC.presence_of_element_located((By.XPATH,'/html/body/div[1]/div/main/section/div[2]'))).get_attribute('outerHTML')
        except:
            pass

        try:
            notice_data.published_date = page_details.find_element(By.XPATH, '/html/body/div[1]/div/main/section/div[2]/div/article/div[1]/div/div/span').text
            notice_data.published_date = re.findall('\d+ \w+ \d{4}', notice_data.published_date)[0]
            notice_data.published_date = dateparser.parse(notice_data.published_date, settings={'DATE_ORDER': 'DMY'})
            notice_data.published_date = str(notice_data.published_date)
            notice_data.published_date = datetime.strptime(notice_data.published_date, '%Y-%m-%d %X').strftime('%Y/%m/%d')
            if notice_data.end_date < notice_data.published_date:
                notice_data.published_date == threshold
        except:
            notice_data.published_date == ''

        if notice_data.published_date == '' and notice_data.end_date == '':
            return

        if notice_data.published_date > notice_data.end_date:
            return

        if notice_data.published_date is not None and notice_data.published_date < threshold:
            return

        try:
            notice_data.resource_url = page_details.find_element(By.CSS_SELECTOR, '.entry-content strong a').get_attribute('href')
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
    th = date.today() - timedelta(10)
    threshold = th.strftime('%Y/%m/%d')
    logging.info("Scraping from or greater than: " + threshold)
    url = 'http://www.ommp.nat.tn/category/appel_offres/'
    logging.info('----------------------------------')
    fn.load_page(page_main, url)
    logging.info(url)
    for page_number in range(2,15):
        page_check = WebDriverWait(page_main, 120).until(EC.presence_of_element_located((By.XPATH,'/html/body/div[1]/div/main/section/div/div[1]/article[1]/div[1]/h2/a'))).text
        for tender_html_element in wait.until(EC.presence_of_element_located((By.XPATH, '/html/body/div[1]/div/main/section/div/div[1]'))).find_elements(By.CSS_SELECTOR, 'article'):
            extract_and_save_notice(tender_html_element)
            if notice_count >= MAX_NOTICES:
                break

            if notice_data.published_date is not None and  notice_data.published_date < threshold:
                break

        try:
            url = 'http://www.ommp.nat.tn/category/appel_offres/page/'+str(page_number)+'/'
            fn.load_page(page_main, url)
            WebDriverWait(page_main, 50).until_not(EC.text_to_be_present_in_element((By.XPATH,'/html/body/div[1]/div/main/section/div/div[1]/article[1]/div[1]/h2/a'),page_check))
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
    output_xml_file.copyFinalXMLToServer("north_america")

