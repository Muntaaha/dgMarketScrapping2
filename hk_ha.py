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
SCRIPT_NAME = "hk_ha"
notice_count = 0
output_xml_file = common.OutputXML.OutputXML(SCRIPT_NAME)

def extract_and_save_notice(tender_html_element):
    global notice_count
    global notice_data
    notice_data = NoticeData()
    notice_data.procurement_method = "Other"
    notice_data.language = "EN"
    notice_data.performance_country = "HongKong"
    notice_data.contact_country = "HongKong"

    if url == urls[2]:

        notice_data.notice_type = 'ca'

        try:
            notice_data.published_date = tender_html_element.find_element(By.CSS_SELECTOR, 'td:nth-of-type(9)').text.strip()
            if 'Date of Award' in notice_data.published_date or notice_data.published_date == '':
                return
            notice_data.published_date = notice_data.published_date.replace('Fabruary','February')
            try:
                notice_data.published_date = re.findall('\d+-\w+-\d{4}', notice_data.published_date)[0]
                notice_data.published_date = datetime.strptime(notice_data.published_date, '%d-%B-%Y').strftime('%Y/%m/%d')
            except:
                notice_data.published_date = re.findall('\d+ \w+ \d{4}', notice_data.published_date)[0]
                notice_data.published_date = datetime.strptime(notice_data.published_date, '%d %B %Y').strftime('%Y/%m/%d')
        except:
            return

        if notice_data.published_date is not None and notice_data.published_date < threshold:
            return

        notice_data.awarding_award_date = notice_data.published_date

        try:
            notice_data.reference = tender_html_element.find_element(By.CSS_SELECTOR, 'td:nth-of-type(2)').text
        except:
            pass

        try:
            notice_data.title_en = tender_html_element.find_element(By.CSS_SELECTOR, 'td:nth-of-type(3)').text.strip()
            notice_data.title_en = GoogleTranslator(source='auto', target='en').translate(notice_data.title_en)
        except:
            pass

        try:
            EOS = tender_html_element.find_element(By.CSS_SELECTOR,'td:nth-of-type(8)').text
            notice_data.est_cost = re.sub("[^\d\.]", "", EOS)
            notice_data.currency = 'HKD'
        except:
            pass

        try:
            notice_data.buyer = tender_html_element.find_element(By.CSS_SELECTOR, 'td:nth-of-type(1)').text.strip()
        except:
            pass

        notice_data.notice_url = url

    else:
        if url == urls[0]:
            notice_data.notice_type = 'spn'
        else:
            notice_data.notice_type = 'eoi'

        try:
            notice_data.end_date = tender_html_element.find_element(By.CSS_SELECTOR, 'td:nth-of-type(3) p').text
            notice_data.end_date = re.findall('\d+ \w+ \d{4}', notice_data.end_date)[0]
            notice_data.end_date = datetime.strptime(notice_data.end_date, '%d %B %Y').strftime('%Y/%m/%d')
        except:
            pass

        if notice_data.end_date is not None and notice_data.end_date < threshold:
            return

        try:
            notice_data.reference = tender_html_element.find_element(By.CSS_SELECTOR, 'td:nth-of-type(1) p').text
        except:
            pass

        try:
            notice_data.title_en = tender_html_element.find_element(By.CSS_SELECTOR, 'td:nth-of-type(2) a').text.strip()
            notice_data.title_en = GoogleTranslator(source='auto', target='en').translate(notice_data.title_en)
        except:
            pass

        try:
            notice_data.buyer = tender_html_element.find_element(By.CSS_SELECTOR, 'td:nth-of-type(4) p').text.strip()
        except:
            pass

        try:
            notice_data.notice_url = page_main.find_element(By.CSS_SELECTOR, 'td:nth-of-type(2) a').get_attribute('href')
            fn.load_page(page_details, notice_data.notice_url)
            try:
                notice_data.notice_text += wait_detail.until(EC.presence_of_element_located((By.XPATH,'/html/body/div/table/tbody'))).get_attribute('outerHTML')
            except:
                pass

            try:
                notice_data.resource_url = page_details.find_element(By.XPATH, '/html/body/div/table/tbody/tr[12]/td[3]/a').get_attribute('href')
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
    main_url = 'https://www.ha.org.hk/visitor/ha_visitor_index.asp?Content_ID=2001&Lang=ENG&Dimension=100&Ver=HTML'
    logging.info('----------------------------------')
    fn.load_page(page_main, main_url)
    iframe = page_main.find_element_by_xpath("/html/body/div[2]/div/div[4]/div[2]/div/iframe")
    page_main.switch_to.frame(iframe)

    page_check = WebDriverWait(page_main, 120).until(EC.presence_of_element_located((By.XPATH,'/html/body/div/table/tbody/tr[1]/td/p[3]/table/tbody/tr[2]/td[3]/a'))).text
        
    spn_url = WebDriverWait(page_main, 120).until(EC.presence_of_element_located((By.XPATH,'/html/body/div/table/tbody/tr[1]/td/p[3]/table/tbody/tr[2]/td[3]/a'))).get_attribute('href')
    eoi_url = WebDriverWait(page_main, 120).until(EC.presence_of_element_located((By.XPATH,'/html/body/div/table/tbody/tr[1]/td/p[3]/table/tbody/tr[4]/td[3]/a'))).get_attribute('href')
    ca_url = WebDriverWait(page_main, 120).until(EC.presence_of_element_located((By.XPATH,'/html/body/div/table/tbody/tr[1]/td/p[3]/table/tbody/tr[6]/td[3]/a'))).get_attribute('href')
    
    page_main.switch_to.default_content()

    urls = [spn_url, eoi_url, ca_url]
    for url in urls:
        fn.load_page(page_main, url)
        logging.info(url)
        if url != urls[2]:
            page_check = WebDriverWait(page_main, 120).until(EC.presence_of_element_located((By.XPATH,'/html/body/div/table[2]/tbody/tr[3]/td[2]/a'))).text

            for tender_html_element in wait.until(EC.presence_of_element_located((By.XPATH, '/html/body/div/table[2]/tbody'))).find_elements(By.CSS_SELECTOR, 'tr')[2:]:
                extract_and_save_notice(tender_html_element)
                if notice_count >= MAX_NOTICES:
                    break

                if notice_data.end_date is not None and  notice_data.end_date < threshold:
                    break
        else:
            page_check = WebDriverWait(page_main, 120).until(EC.presence_of_element_located((By.XPATH,'/html/body/div/table/tbody/tr[8]/td[1]'))).text
            for tender_html_element in wait.until(EC.presence_of_element_located((By.XPATH, '/html/body/div/table/tbody'))).find_elements(By.CSS_SELECTOR, 'tr')[7:]:
                extract_and_save_notice(tender_html_element)
                if notice_count >= MAX_NOTICES:
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
    output_xml_file.copyFinalXMLToServer("asia")

