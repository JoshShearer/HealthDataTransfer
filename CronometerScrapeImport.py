from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import Select
from time import sleep
import os
import pandas as pd
import unittest
from datetime import date, datetime, timedelta
import glob
import re

RECENT_CUTOFF_DATE = date(2021,12,28)
# OLD_CUTOFF_DATE = date(2013,3,17) #nutrition ==> LabResults date(2017,5,22)
OLD_CUTOFF_DATE = date(2021,2,8) #nutrition
AM = 'AM'
PM = 'PM'
MIN_WAIT = 0
SHORT_WAIT = MIN_WAIT + 1
MEDIUM_WAIT = MIN_WAIT + 3
LONG_WAIT = MIN_WAIT + 5
MAX_WAIT = MIN_WAIT + 10
APP_BIOMETRICS = ['Weight','Height','Systolic Blood Pressure','Diastolic Blood Pressure',
                  'Blood Glucose','Body Temperature','Body Fat','Waist Size','Total Cholesterol',
                  'LDL Cholesterol','HDL Cholesterol','Triglycerides','Mood','Ketones(Blood)',
                  'Sleep','Ketones(Urine)','Ketones(Breath)','25-Hydroxy Vitamin D','Ferritin',
                  'Pulse Wave Velocity']
MFP_MACROS = ['Energy', 'Fat', 'Saturated', 'Polyunsaturated', 'Monounsaturated', 'Trans-Fat', 'Cholesterol', 'Sodium', 'Potassium', 'Carbohydrates', 'Fiber', 'Sugars', 'Protein', 'Vitamin A', 'Vitamin C', 'Calcium', 'Iron']
NUTRIENT_MACROS = ['Energy', 'Fat', 'Saturated', 'Polyunsaturated', 'Monounsaturated', 'Trans-Fats', 'Cholesterol', 'Sodium', 'Potassium', 'Carbs', 'Fiber', 'Sugars', 'Protein', 'Vitamin A', 'Vitamin C', 'Calcium', 'Iron']
headers = {    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.143 Safari/537.36'}

def get_current_page_date(driver):


    #   #error caused by page loadin times durring slow internet
    try:
        date = driver.find_element_by_css_selector(".GJES3IWDDQD:nth-child(2)") #date = driver.find_elements_by_xpath('//div[@class="GHDCC5OBBSC"]')
        date = date.text.strip()
        current_date = datetime.strptime(date,'%B %d, %Y')
    except Exception as e:
        print(e)
        try:
            date = driver.find_element_by_xpath('//div[@class="GJES3IWDDQD"]')
            date = date.text.strip()
            current_date = datetime.strptime(date,'%B %d, %Y')
        except Exception as e:
            print("issues scraping date information.  Revise code")
            print(e)
    return (driver, current_date)

def calc_date_diff(current_date, next):

    difference = abs(current_date - next)
    next_date = current_date - timedelta(days=difference.days)
    if current_date > next:
        direction = 'past'
    elif current_date < next:
        direction = 'future'
    else:
        direction = 'equal'
        return (direction, 0, 0, 0)

    if difference.days > 365:
        years = difference.days // 365
        days = difference.days - (years * 365)
        if days > 30:
            months = days // 30
            days = days - (months * 30)
        else:
            months = 0
    elif difference.days > 30:
        months = difference.days // 30
        days = difference.days - (months * 30)
        years = 0
    else:
        days = abs(difference.days)
        months = 0
        years = 0
    return direction, days, months, years

def webpage_nav(next_date,driver):
    page_found = False
    while not page_found:
        sleep(MIN_WAIT)
        driver, current_date = get_current_page_date(driver)
        direction, days, months, years = calc_date_diff(current_date,next_date)
        if direction == 'equal':
            page_found = True
            return driver
        else:
            driver = webpage_navigation_date(direction, days, months, years, driver)
    return driver

def webpage_navigation_date(direction, days, months, years,driver):

    left_year = driver.find_elements_by_xpath("//div[@class='datePickerPreviousYearButton datePickerPreviousYearButton-up']")
    right_year = driver.find_elements_by_xpath("//div[@class='datePickerNextYearButton datePickerNextYearButton-up']")
    left_day = driver.find_elements_by_xpath("//button[@class='GJES3IWDIQD GJES3IWDGQD']")
    right_day = driver.find_elements_by_xpath("//button[@class='GJES3IWDHQD GJES3IWDGQD']") #xpath=//div[@id='cronometerApp']/div[2]/div/div/table/tbody/tr/td/div/div/div/button[2]
    cal_days = driver.find_elements_by_xpath("//tr[2]/td/div") #what the fuck is this again?
    #cal_days = driver.find_elements_by_xpath("//div[@class='datePickerDay  datePickerDayIsToday  day-has-data  datePickerDayIsValue ']")
    left_month = driver.find_elements_by_css_selector(".datePickerPreviousButton > .html-face")
    right_month = driver.find_elements_by_css_selector(".datePickerNextButton > .html-face")
    try:
        if direction == "past":
            for year in range(years):
                left_year[0].click()
            for month in range(months):
                left_month[0].click()
            for index, day in enumerate(range(days)):
                # if index < 1:
                    # cal_days[0].click()
                left_day[0].click()
            if days == 0:
                cal_days[0].click()
        else:
            for year in range(years):
                right_year[0].click()
            for month in range(months):
                right_month[0].click()
            for index, day in enumerate(range(days)):
                if index < 1 and (years > 0 or months > 3):
                    cal_days[0].click()
                right_day[0].click()
            if days == 0:
                cal_days[0].click()
    except:
        print('calender buttons were not captured correctly please revise code')

    return driver

def enter_biometric_data(biometrics,driver):

    if biometrics.filename == 'BloodNutrientTracking.csv':
        #Navigate to correct page
        # driver = webpage_nav(biometrics.Date, driver)
        time_entry = False
        #Prepare time entry
        try:
            time_cap = []
            time_pattern = re.compile("(\d{1,2}:\d{2})(?i)(am|pm)")
            time_cap = re.split(time_pattern, biometrics.Time)
            hour,minute = time_cap[1].split(':')
            morn_aft = time_cap[2]
            if re.match(r"(?i)(pm)", morn_aft):
                time_entry = True
                morn_aft = PM
            else:
                morn_aft = AM
        except:
            print("time data not available")
        hour_css = ".GHDCC5OBA0B"
        ampm_xpath = "//div/select"


        # driver = webpage_nav(biometrics.Date, driver)
        #Navigate to the selection menu
        Biometric_button = driver.find_elements_by_xpath("//span[contains(.,'ADD BIOMETRIC')]")
        Biometric_button[0].click()
        sleep(SHORT_WAIT)
        # drop_down = driver.find_element_by_css_selector("td:nth-child(1) > .gwt-ListBox")
        # drop_down.click()
        # select = Select(drop_down)
        send_string_keys("Ketones (Blood)", driver)
        driver.find_element_by_xpath("//div[@class='Ketones (Blood)']")
        #Add Ketone Data Followed by Blood Glucose
        # select.select_by_visible_text('Ketones (Blood)')
        # entry = driver.find_element_by_xpath('//td[2]/input')
        send_string_keys(str(biometrics['Ketones']), driver)
        sleep(SHORT_WAIT)


        biometric_tod_button = driver.find_element_by_xpath("//div[@class='GHDCC5OBBGC']//following-sibling::span/input[@type='checkBox']")
        checked = biometric_tod_button.is_selected()
        if not checked:
            sleep(SHORT_WAIT)
            biometric_tod_button.click()

        element_string = '//div[@class="GHDCC5OBBGC" and contains(text(), \':\')]'
        biometric_span = driver.find_elements_by_xpath(element_string)
        biometric_span[len(biometric_span)-1].click()
        sleep(SHORT_WAIT)
        biometric_hour = driver.find_elements_by_css_selector(".gwt-ListBox:nth-child(4)")
        biometric_ampm = driver.find_elements_by_xpath("/html/body/div[6]/div/div/div[2]/div[3]/div/div[1]/select")

        # typical methods are not working, ActionsChains should work here
        # had to replicate code, if statement between action chains causes timing issues
        # if not time_entry:
        actions = ActionChains(driver)
        actions.move_to_element(biometric_hour[0])
        actions.key_down(Keys.CONTROL)
        actions.send_keys('a')
        actions.key_up(Keys.CONTROL)
        actions.send_keys(Keys.BACKSPACE)
        actions.pause(2)
        actions.send_keys(str(hour))
        actions.send_keys(Keys.TAB)
        actions.key_down(Keys.CONTROL)
        actions.send_keys('a')
        actions.key_up(Keys.CONTROL)
        actions.send_keys(Keys.BACKSPACE)
        actions.send_keys(str(minute))
        actions.perform()
        actions.pause(2)
        # actions.send_keys(Keys.ENTER)
        select = Select(biometric_ampm[len(biometric_ampm)-1])
        select.select_by_visible_text(morn_aft)

        test = driver.find_elements_by_xpath("//button[contains(.,'Add')]")
        sleep(MEDIUM_WAIT)
        test[len(test) - 1].click()
        sleep(SHORT_WAIT)

        # test = driver.find_elements_by_xpath("//button[@class='btn-orange-flat GHDCC50BM3C'")


        #Now Blood Glucose Info
        try:
            BC = biometrics['Blood Sugar']
            Biometric_button = driver.find_elements_by_xpath("//span[contains(.,'ADD BIOMETRIC')]")
            Biometric_button[0].click()
            sleep(MEDIUM_WAIT)
            # drop_down = driver.find_element_by_css_selector("td:nth-child(1) > .gwt-ListBox")
            # drop_down.click()
            # select = Select(drop_down)
            send_string_keys("Blood Glucose", driver)
            driver.find_element_by_xpath("//div[@class='Blood Glucose']")
            #Add Ketone Data Followed by Blood Glucose
            # select.select_by_visible_text('Blood Glucose')
            # entry = driver.find_element_by_xpath('//td[2]/input')
            sleep(SHORT_WAIT)
            send_string_keys(str(BC), driver)

            # try:
            #     biometric_tod_button = driver.find_element_by_xpath("/html/body/div[6]/div/div/div[2]/div[4]/div[1]/div[2]/span/input")
            # except:
            #     print('trouble finding the TOD button, trying another way')
            # try:
            #     biometric_tod_button = driver.find_elements_by_xpath("/html/body/div[6]/div/div/div[2]/div[3]/div/span/input")
            # except:
            #     print('trouble finding the TOD button, trying another way')

            biometric_tod_button = driver.find_element_by_xpath("//div[@class='GHDCC5OBBGC']//following-sibling::span/input[@type='checkBox']")
            checked = biometric_tod_button.is_selected()
            if not checked:
                sleep(SHORT_WAIT)
                biometric_tod_button.click()

            element_string = '//div[@class="GHDCC5OBBGC" and contains(text(), \':\')]'
            biometric_span = driver.find_elements_by_xpath(element_string)
            biometric_span[len(biometric_span)-1].click()

            biometric_span[len(biometric_span)-1].click()
            biometric_hour = driver.find_elements_by_css_selector(".gwt-ListBox:nth-child(4)")
            biometric_ampm = driver.find_elements_by_xpath("//div/select")

            # typical methods are not working, ActionsChains should work here
            # had to replicate code, if statement between action chains causes timing issues
            actions = ActionChains(driver)
            actions.move_to_element(biometric_hour[0])
            actions.key_down(Keys.CONTROL)
            actions.send_keys('a')
            actions.key_up(Keys.CONTROL)
            actions.send_keys(Keys.BACKSPACE)
            actions.pause(1)
            actions.send_keys(str(hour))
            actions.send_keys(Keys.TAB)
            actions.key_down(Keys.CONTROL)
            actions.send_keys('a')
            actions.key_up(Keys.CONTROL)
            actions.send_keys(Keys.BACKSPACE)
            actions.send_keys(str(minute))
            actions.pause(1)
            actions.perform()
            # actions.send_keys(Keys.ENTER)
            select = Select(biometric_ampm[len(biometric_ampm)-1])
            select.select_by_visible_text(morn_aft)

            test = driver.find_elements_by_xpath("//button[contains(.,'Add')]")
            sleep(MEDIUM_WAIT)
            test[len(test) - 1].click()
            sleep(SHORT_WAIT)

        except:
            print("No Blood Glucose Data Found")

        #Look at adding the note
        try:
            note_data = biometrics['Notes']
            try:
                activity_data = biometrics['Activity Level']
                note_data = 'Activity Data => ' + activity_data + ' '+ note_data
            except:
                print('Did not find any activity data associated with Biometric Entry')

            add_note_menu = driver.find_elements_by_xpath("//span[contains(.,'ADD NOTE')]")
            add_note_menu[0].click()
            sleep(MEDIUM_WAIT)
            send_string_keys(note_data, driver)
            biometric_tod_button = driver.find_element_by_xpath("//div[@class='GHDCC5OBBGC']//following-sibling::span/input[@type='checkBox']")
            checked = biometric_tod_button.is_selected()
            if checked:
                # biometric_span = driver.find_elements_by_xpath("//div[3]/div/div[2]/span")
                # checked = driver.find_elements_by_xpath("//input[@type='checkbox' and (@checked)]")
                element_string = '//span[@class="GHDCC5OBA0B" and contains(text(), \':\')]'
                biometric_span = driver.find_elements_by_xpath(element_string)

            else:
                # biometric_tod_button = driver.find_elements_by_xpath('//input[@type="checkbox"]')
                biometric_tod_button = driver.find_elements_by_xpath("//div[2]/div[3]/div/span/input")
                sleep(SHORT_WAIT)
                biometric_tod_button[len(biometric_tod_button) - 1].click()
                # biometric_span = driver.find_elements_by_xpath("//div[3]/div/div[2]/span")
                biometric_span = driver.find_elements_by_xpath("//span[@class='GHDCC5OBA0B']")

            biometric_span[len(biometric_span)-1].click()
            biometric_hour = driver.find_elements_by_css_selector(".gwt-ListBox:nth-child(4)")
            biometric_ampm = driver.find_elements_by_xpath("//div/select")
            # typical methods are not working, ActionsChains should work here
            # had to replicate code, if statement between action chains causes timing issues
            actions = ActionChains(driver)
            actions.move_to_element(biometric_hour[0])
            actions.key_down(Keys.CONTROL)
            actions.send_keys('a')
            actions.key_up(Keys.CONTROL)
            actions.send_keys(Keys.BACKSPACE)
            actions.pause(1)
            actions.send_keys(str(hour))
            actions.send_keys(Keys.TAB)
            actions.key_down(Keys.CONTROL)
            actions.send_keys('a')
            actions.key_up(Keys.CONTROL)
            actions.send_keys(Keys.BACKSPACE)
            actions.send_keys(str(minute))
            actions.pause(1)
            actions.perform()
            # actions.send_keys(Keys.ENTER)
            select = Select(biometric_ampm[len(biometric_ampm)-1])
            select.select_by_visible_text(morn_aft)

            test = driver.find_element_by_xpath("//button[contains(.,'Save Note')]")
            test.click()

        except:
            print("No note data found")


    elif biometrics.filename == 'Measurement-Summary.csv':
        #Navigate to the selection menu
        Biometric_button = driver.find_elements_by_xpath("//span[contains(.,'ADD BIOMETRIC')]")
        Biometric_button[0].click()
        sleep(MEDIUM_WAIT)

        entry = driver.find_element_by_xpath("//td[2]/input")
        # entry.click()
        send_string_keys(str(biometrics.Weight), driver)
        # test = driver.find_element_by_xpath("//button[text()='Add']") #sometimes captures text = ''???
        test = driver.find_elements_by_xpath("/html/body/div[6]/div/div/div[2]/div[5]/button")
        test[0].click()

    elif biometrics.filename == 'LabResults.csv':
        sleep(MEDIUM_WAIT)
        Biometric_button = driver.find_elements_by_xpath("//span[contains(.,'ADD BIOMETRIC')]")
        Biometric_button[0].click()
        sleep(MEDIUM_WAIT)
        if biometrics['Marker Name'] in APP_BIOMETRICS:
            # actions = ActionChains(driver)
            # actions.send_keys(Keys.ESCAPE)
            # actions.perform()
            # return driver
            for metric in APP_BIOMETRICS:
                if metric == biometrics['Marker Name']:
                    #Navigate to the selection menu
                    driver = webpage_nav(biometrics.Date, driver)
                    send_string_keys(biometrics['Marker Name'], driver)
                                # bios = "//option[@value='%s']" % row
                                # drop_down = driver.find_element_by_xpath(bios)
                                # drop_down.click()
                                # send_string_keys(str(biometrics['Value']), driver)
                    bios = "//div[@style='background-color: rgb(250, 249, 247);']"#contains(text(), \'%s\')]" % biometrics['Marker Name']
                    test = driver.find_elements_by_xpath(bios)
                    sleep(SHORT_WAIT)
                    check_valid_path(test)
                    send_string_keys(biometrics['Value'],driver)
                    actions = ActionChains(driver)
                    actions.send_keys(Keys.TAB)
                    actions.send_keys(Keys.TAB)
                    actions.send_keys(Keys.TAB)
                    actions.perform()
                    send_string_keys('Uncategorized', driver)
                    select = driver.find_elements_by_xpath("//button[contains(.,'Add to Diary')]")
                    select[0].click()
            #         actions = ActionChains(driver)
            #         actions.send_keys(Keys.ESCAPE)
            #         actions.perform()
            #         return driver
        else:
            custom_bio_string = biometrics["Marker Name"] + ' - ' + biometrics["Marker Description"]
            custom_bio_string = custom_bio_string.strip()
            send_string_keys(custom_bio_string, driver)
            try: #test whether this custom bio has already been added
                bio_xpath = "//div[./text()=\'%s\']" % custom_bio_string
                custom_biometric = driver.find_elements_by_xpath(bio_xpath)
                test = custom_biometric[0] #trip exception if array is empty => no results
                check_valid_path(custom_biometric)
                sleep(MIN_WAIT)
                data_entry_box = driver.find_elements_by_xpath("//div[@class='GJES3IWDCKE']")
                data_entry_box[0].click()
                send_string_keys(biometrics["Value"], driver)
                actions = ActionChains(driver)
                actions.send_keys(Keys.TAB)
                actions.send_keys(Keys.TAB)
                actions.send_keys(Keys.TAB)
                actions.perform()
            except Exception as e: #not added
                print(e)
            #Add Custom Metric
                custom_button = driver.find_element_by_xpath("//button[contains(.,'Add Custom Biometric')]")
                custom_button.click()
                send_string_keys(biometrics["Marker Name"] + ' - ' + biometrics["Marker Description"], driver)
                units = driver.find_element_by_xpath("//input[@placeholder='My Custom Unit']")
                units.click()
                actions = ActionChains(driver)
                if "Units" in biometrics.index:
                    send_string_keys(biometrics["Units"], driver)
                else:
                    send_string_keys('nan', driver)
                # driver.find_element_by_xpath("//input[@class='gwt-ListBox GHDCC5OBFUC']").click()
                actions.send_keys(Keys.TAB)
                actions.perform()
                send_string_keys(biometrics["Value"], driver)
                actions = ActionChains(driver)
                actions.send_keys(Keys.TAB)
                actions.send_keys(Keys.TAB)
                actions.perform()
            send_string_keys('Uncategorized', driver)
            select = driver.find_elements_by_xpath("//button[./text()='Add to Diary']")
            for nodes in select:
                if nodes.text == 'Add to Diary':
                    nodes.click()

    return driver

def enter_exercise_data(exercise, driver):
    #Navigate to the selection menu
    hours, minutes, seconds = exercise['Activity Time'].split(':')
    hours = int(hours)
    minutes = int(minutes)
    if hours > 0:
        minutes += hours * 60
    # driver = webpage_nav(exercise.Date, driver)
    Exercise_button = driver.find_elements_by_xpath("//span[contains(.,'ADD EXERCISE')]")
    Exercise_button[0].click()
    sleep(MEDIUM_WAIT)
    exercise_title = driver.find_element_by_xpath("/html/body/div[6]/div/div/table/tbody/tr[3]/td/div/input")
    exercise_title.clear()
    exercise_title.send_keys(str(exercise['Title']))
    exercise_time = driver.find_element_by_xpath("/html/body/div[6]/div/div/table/tbody/tr[3]/td/div/div[3]/input[1]")
    exercise_time.clear()
    exercise_time.send_keys(str(minutes))
    calorie_burn = driver.find_element_by_xpath("/html/body/div[6]/div/div/table/tbody/tr[3]/td/div/div[3]/input[2]")
    calorie_burn.clear()
    calorie_burn.send_keys(str(exercise['Calories']))

    #tod entry info ...if necessary
    try:
        # prep the time information if exists
        hour, minute = exercise.Time.split(':')
        hour = int(hour)
        PM = False
        if hour > 11:
            PM = True
            if hour != 12:
                hour = hour - 12

        exercise_tod_button = driver.find_elements_by_xpath("/html/body/div[6]/div/div/table/tbody/tr[3]/td/div/div[4]/div[1]/div/span")
        exercise_tod_button[0].click()
        exercise_span = driver.find_elements_by_xpath("/html/body/div[6]/div/div/table/tbody/tr[3]/td/div/div[4]/div[1]/div/div[2]/span")
        exercise_span[0].click()
        exercise_hour = driver.find_elements_by_css_selector(".gwt-TextBox:nth-child(3)")
        exercise_ampm = driver.find_elements_by_css_selector("//div/select")

        # typical methods are not working, ActionsChains should work here
        # had to replicate code, if statement between action chains causes timing issues
        if not PM:
            actions = ActionChains(driver)
            actions.move_to_element(exercise_hour[0])
            actions.key_down(Keys.CONTROL)
            actions.send_keys('a')
            actions.key_up(Keys.CONTROL)
            actions.send_keys(Keys.BACKSPACE)
            actions.pause(2)
            actions.send_keys(str(hour))
            actions.send_keys(Keys.TAB)
            actions.key_down(Keys.CONTROL)
            actions.send_keys('a')
            actions.key_up(Keys.CONTROL)
            actions.send_keys(Keys.BACKSPACE)
            actions.send_keys(str(minute))
            actions.pause(2)
            # actions.send_keys(Keys.ENTER)
            actions.click(exercise_ampm[0])
            actions.send_keys(Keys.ARROW_UP)
            actions.send_keys(Keys.ENTER)
            actions.perform()
        else:
            actions = ActionChains(driver)
            actions.move_to_element(exercise_hour[0])
            actions.key_down(Keys.CONTROL)
            actions.send_keys('a')
            actions.key_up(Keys.CONTROL)
            actions.send_keys(Keys.BACKSPACE)
            actions.pause(2)
            actions.send_keys(str(hour))
            actions.send_keys(Keys.TAB)
            actions.key_down(Keys.CONTROL)
            actions.send_keys('a')
            actions.key_up(Keys.CONTROL)
            actions.send_keys(Keys.BACKSPACE)
            actions.send_keys(str(minute))
            actions.pause(2)
            # actions.send_keys(Keys.ENTER)
            actions.click(exercise_ampm[0])
            actions.send_keys(Keys.ARROW_DOWN)
            actions.send_keys(Keys.ENTER)
            actions.perform()
    except:
        print('No time data found for exercise')

    add_exercise_data = driver.find_element_by_xpath("//button[contains(.,'Add')]")
    add_exercise_data.click()
    return driver

def send_string_keys(string, driver):
    sleep(.5)
    actions = ActionChains(driver)
    actions.send_keys(string)
    actions.perform()
    actions.reset_actions()
    return driver
    
def send_ind_keys(string, driver):
    sleep(.5)
    actions = ActionChains(driver)
    for char in string:
        actions.key_down(char)
        actions.key_up(char)
        actions.pause(1)
        actions.perform()
    return driver

def delete_table_data(row, driver):

    # print('Navigating to ' + str(date))
    # driver = webpage_nav(date, driver)
    #search out Weight
    time_str = str(row.Date).split(' ')
    to_delete = (str(time_str[0]) + str(row.Meal))
    print('Attempting to Delete ' + to_delete)

    try:
        delete_xpath = '//div[contains(text(), \'%s\')]' % to_delete
        entry = driver.find_element_by_xpath(delete_xpath)
        sleep(MEDIUM_WAIT)
        # entry.click()
        actionChains = ActionChains(driver)
        actionChains.context_click(entry).perform()
        sleep(MEDIUM_WAIT)
        delete = driver.find_elements_by_xpath('//div[contains(text(), \'Delete Selected Items\')]')
        delete[len(delete) - 1].click()
        sleep(MEDIUM_WAIT)
        validate = driver.find_elements_by_xpath("//span[contains(.,'Yes')]/parent::*")
        validate[len(validate) - 1].click()
        sleep(MEDIUM_WAIT)
    except Exception as e:
        print('Did not find any Table Data, please verify string is correct')
        print(e)
    # CURRENT_DATE = CURRENT_DATE + timedelta(days=1)
    return driver

def check_valid_path(results):
    for i, search_result in enumerate(results):
        if search_result.location['x'] != 0 and search_result.location['y'] != 0:
            results[i].click()
            break

def add_food_data(food_data, driver):
    #Navigate to the custom food tabs and create new
    # driver = webpage_nav(food_data.Date, driver)
    Foods_button = driver.find_elements_by_xpath("//a[contains(text(),'Foods')]")
    # Foods_button = driver.find_elements_by_css_selector(".main-nav-active > a")
    Foods_button[len(Foods_button) - 1].click()
    Custom_Foods = driver.find_elements_by_xpath("//div[@id='cronometerApp']/div[2]/div[3]/div/div/table/tbody/tr/td/table/tbody/tr/td[3]/table/tbody/tr[2]/td[2]/div/div/div")
    # Custom_Foods = driver.find_elements_by_css_selector(".gwt-TabBarItem-wrapper:nth-child(3) .gwt-Label")
    Custom_Foods[len(Custom_Foods) - 1].click()
    Add_Food = driver.find_elements_by_xpath("//button[contains(.,'+ Add Food')]")
    Add_Food[len(Add_Food) - 1].click()


    #Enter Data
    #Name
    Name_entry = driver.find_elements_by_xpath("//input[@title='New Food']")
    Name_entry[0].clear()
    Name_entry[0].click()
    time_str = str(food_data.Date).split(' ')
    new_temp_food = str(time_str[0] + food_data.Meal)
    Name_entry[0].send_keys(new_temp_food)
    #Note
    Note_entry = driver.find_elements_by_xpath("//div[@class='gwt-Label' and contains(.,'Notes')]//following-sibling::div/textarea[@class='gwt-TextArea']")
    Note_entry[1].send_keys("MFPUpload")

    # Caloric Information
    # Energy
    for index, nutrient in enumerate(MFP_MACROS):
        xpath_string = "//div[@class='gwt-HTML' and contains(text(), \'%s\')]" % NUTRIENT_MACROS[index]
        current_nutrient = driver.find_elements_by_xpath(xpath_string)
        for i, search_result in enumerate(current_nutrient):
            if search_result.location['x'] != 0 and search_result.location['y'] != 0:
                current_nutrient[i].click()
                break
        actions = ActionChains(driver)
        send_string_keys(str(food_data[nutrient]), driver)
        sleep(MIN_WAIT)

    #save Data and add to day
    save = driver.find_elements_by_xpath("//button[contains(text(), 'Save Changes')]")
    check_valid_path(save)
    sleep(MEDIUM_WAIT)

    #return to diary
    diary = driver.find_elements_by_xpath("//a[@href='#diary' and contains(text(), 'Diary')]")
    check_valid_path(diary)
    sleep(MEDIUM_WAIT)

    #add food
    food = driver.find_elements_by_xpath("//span[contains(.,'ADD FOOD')]")
    sleep(SHORT_WAIT)
    check_valid_path(food)
    sleep(MAX_WAIT)
    send_string_keys(new_temp_food,driver)
    sleep(MEDIUM_WAIT)

    #Guessing this should be the first element in the list
    selector = ('//div[text()="%s"]') % new_temp_food
    current_meal = driver.find_elements_by_xpath(selector)
    current_meal[len(current_meal)-1].click() #last selection available if accidently added twice
    # current_meal[0].click() #possible to break
    sleep(MEDIUM_WAIT)

    #select category
    category_menu = driver.find_elements_by_xpath("//button[@class='GHDCC5OBG1D']")
    category_menu[0].click()
    sleep(MEDIUM_WAIT)
    # table = driver.find_elements_by_xpath("/html/body/div[6]/div")
    # select = Select(table[0])
    # select.select_by_visible_text(food_data.Meal)
    meal_finder = '//div[@class="gwt-Label prettyPopupMenuItem" and contains(text(), \'%s\')]/parent::*' % food_data.Meal
    menu_select = driver.find_elements_by_xpath(meal_finder)
    menu_select[0].click()

    select = driver.find_elements_by_xpath("//button[contains(.,'Add')]")
    select[len(select)-1].click()

    #return to the foods tab and retire the food
    Foods_button[0].click()
    Custom_Foods[0].click()
    # search_bar = driver.find_elements_by_xpath("//div[@id='cronometerApp']/div[2]/div[3]/div/div/table/tbody/tr[2]/td/div/div/div/div/div/div/div[2]/input")
    # search_bar[0].click()
    # send_string_keys(new_temp_food,driver)
    # food_match = driver.find_elements_by_xpath("/html/body/div[1]/div[4]/div[2]/div[3]/div/div/table/tbody/tr[2]/td/div/div[2]/div/div/div[1]/div[1]/div[4]/div/div/table/tbody/tr[1]/td/a")
    # food_match[0].click()
    remove_menu = driver.find_elements_by_xpath("//img[@class='gwt-Image GHDCC5OBKP']")
    check_valid_path(remove_menu)
    sleep(SHORT_WAIT)
    retire_popup = driver.find_elements_by_css_selector("tr:nth-child(1) .prettyPopupMenuItem")
    retire_popup[0].click()
    sleep(MEDIUM_WAIT)
    # retire_button = driver.find_elements_by_xpath("/html/body/div[6]/div/div/table[2]/tbody/tr/td[2]/button/span")
    retire_button = driver.find_elements_by_xpath("//span[text()='Retire']/parent::*")
    retire_button[0].click()
    sleep(SHORT_WAIT)

    # #return to diary
    diary = driver.find_elements_by_xpath('//div[2]/div/ul/li/a')
    diary[0].click()
    return driver

def check_date_column(df):
    #validate date exists
    date = False
    cols = list(df)
    split = False
    date_column_index = 0
    for index, column in enumerate(cols):
        column = column.strip()
        if re.search('Date', column):
            date = True
            date_column_index = index
            date_column_name = cols[index]
        #Remove units from column names for cleaner usage later
        if re.match(r'(\w+\s)+\(.*\)$', column):
            words = []
            measurement = ''
            words = column.split(' ')
            for i, word in enumerate(words):
                if i == (len(words)-1):
                    units = word
                else:
                    if i > 0:
                        measurement += (" " + word)
                    else:
                        measurement = word

            df.rename(columns={column:measurement}, inplace=True)
    if not date:
        return df
    #Check formatting (may have '\' instead of '-' or include time as well
    df.rename(columns={date_column_name:'Date'}, inplace=True)
    df['Date'] = df.Date.str.replace('/','-')
    for col in df['Date'].str.contains('\d+-\d+-\d+ \d+', regex=True):  #if time is included col needs to be split
        if col and not split:
            df['str_split'] = df['Date'].str.split(' ')
            df['Date'] = df.str_split.str.get(0)
            df['Time'] = df.str_split.str.get(1)
            del df['str_split']
            split = True
    df['Date'] = pd.to_datetime(data['Date'])
    # df['Date'] = df['Date'].dt.date
    return df

# ImportData Collection
files = glob.glob("*.csv")
df_nutrition = []
for filename in files:
  data = pd.read_csv(filename,encoding = "ISO-8859-1")
  data = data.rename(columns={'Day': 'Date'})
  data['filename'] = filename
  data = check_date_column(data)
  df_nutrition.append(data)
df_nutrition_data = pd.concat(df_nutrition)

#Data Cleanup
df_nutrition_data['Date'].fillna(df_nutrition_data['Date'])
df_nutrition_data = df_nutrition_data.sort_values(['Date','Meal'], ascending=[True, True])
df_nutrition_data = df_nutrition_data.set_index("Date", drop = False)

# Login to site and navigate to data entry area
Email = "youremail@gmail.com" #Will need to be changed for your account
Password = 'yourpassword' # Will need to change for your account


# instantiate a chrome options object so you can set the size and headless preference
chrome_options = Options()
# chrome_options.add_argument("--headless")
chrome_options.add_argument("--window-size=1920x1080")

# download the chrome driver from https://sites.google.com/a/chromium.org/chromedriver/downloads and put it in the
# current directory
chrome_driver = os.getcwd() +"\\chromedriver.exe"


# Navigate Cronometer
driver = webdriver.Chrome(options=chrome_options, executable_path=chrome_driver)
driver.get("https://www.cronometer.com/")
current_page = driver.current_url
# sleep(LONG_WAIT)
driver.get_screenshot_as_file("Enter.png")

login_button = driver.find_element_by_xpath("//a[contains(@href, 'login/')]")
login_button.click()



#sign into the site
username = driver.find_element_by_id("usernameBox")
# username =
username.clear()
username.send_keys(Email)

password = driver.find_element_by_name("password")
password.clear()
password.send_keys(Password)
driver.find_element_by_id("login-button").click()
# capture the screen
sleep(MAX_WAIT)

# Iterate over the data and enter into website
#delete_table_data(driver)
current_date = ''
for i, row in df_nutrition_data.iterrows():
    row = row.dropna()
    if row.Date.date() < RECENT_CUTOFF_DATE and row.Date.date() > OLD_CUTOFF_DATE:
        print("Uploading data for " + row.filename + " => " + str(row.Date))
        if current_date != row.Date:
            driver = webpage_nav(row.Date, driver)
        if (row.filename == 'BloodNutrientTracking.csv' or
             row.filename == 'Measurement-Summary.csv' or
            row.filename == 'LabResults.csv'):
            driver = enter_biometric_data(row, driver)
        elif row.filename == 'Activities.csv':
            driver = enter_exercise_data(row,driver)
        if row.filename == 'Nutrition-Summary.csv':
            driver = add_food_data(row, driver)
            driver = delete_table_data(row, driver)
        current_date = row.Date

