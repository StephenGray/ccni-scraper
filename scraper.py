# This is a template for a Python scraper on morph.io (https://morph.io)
# including some code snippets below that you should find helpful

# import scraperwiki
# import lxml.html
#
# # Read in a page
# html = scraperwiki.scrape("http://foo.com")
#
# # Find something on the page using css selectors
# root = lxml.html.fromstring(html)
# root.cssselect("div[align='left']")
#
# # Write out to the sqlite database using scraperwiki library
# scraperwiki.sqlite.save(unique_keys=['name'], data={"name": "susan", "occupation": "software developer"})
#
# # An arbitrary query against the database
# scraperwiki.sql.select("* from data where 'name'='peter'")

# You don't have to do things with the ScraperWiki and lxml libraries.
# You can use whatever libraries you want: https://morph.io/documentation/python
# All that matters is that your final data is written to an SQLite database
# called "data.sqlite" in the current working directory which has at least a table
# called "data".
# This is a template for a Python scraper on morph.io (https://morph.io)
# including some code snippets below that you should find helpful

# You don't have to do things with the ScraperWiki and lxml libraries.
# You can use whatever libraries you want: https://morph.io/documentation/python
# All that matters is that your final data is written to an SQLite database
# called "data.sqlite" in the current working directory which has at least a table
# called "data".

from lxml import html
import urllib2, requests, csv, os, sqlite3
from datetime import date

def set_up_table(table_name):
    c.execute('CREATE TABLE IF NOT EXISTS ' + table_name + '(id INTEGER PRIMARY KEY)')
    conn.commit()
    try:
        c.execute("ALTER TABLE {tn} ADD COLUMN 'data_acquire_date'".format(tn=table_name))
        conn.commit()
        print("Table created")
    except:
        pass

def get_charity_nums(charity_nums):
    response = urllib2.urlopen('https://www.charitycommissionni.org.uk/umbraco/api/charityApi/ExportSearchResultsToCsv/?pageNumber=1&include=Linked&include=Removed')
    print("List downloaded")
    f = csv.reader(response.read().splitlines())
    for line in f:
        charity_nums.append(line[0])

    ## write each charity no. to the SqliteDB as PRIMARY KEYs
    for nic in charity_nums[1:]:
        try:
            c.execute("INSERT OR IGNORE INTO {tn} (id) VALUES ({nic})".\
                format(tn=table_name, nic=nic))
            conn.commit()
        except sqlite3.IntegrityError:
            print('ERROR: ID already exists in PRIMARY KEY column {}'.format(nic))

def get_fieldnames():
    # get fieldnames first from the FIELDS_xPATH file
    fieldnames = []
    xpaths = []
    with open('fields_xpath.txt', 'r') as fieldfile:
        reader = csv.DictReader(fieldfile)
        for row in reader:
            fieldnames.append(row['Field'])
            xpaths.append(row['xPath'])
            ## write each field heading to the SqliteDB so we can write later
            try:
                c.execute("ALTER TABLE {tn} ADD COLUMN '{cn}'"\
                    .format(tn=table_name, cn=row['Field']))
                conn.commit()
            except:
                pass

    pairings = list(zip(fieldnames, xpaths))
    return(pairings)

def scrape_write_data(charity_num, page, pairings):
    ''' #TODO: Status and Company number fields may not be found correctly
        as their list order can change depending what data is available. 
        May need to use Regex to counter this.
    '''
    tree = html.fromstring(page.content)
    # go through each field in the xPath set and scrape data
    if page.status_code == requests.codes.ok:
        for field in pairings:
            fieldvalue = tree.xpath(field[1])
            newfieldvalue = []
            for listitem in fieldvalue:
                listitem.replace(' +',' ') # doesn't seem to be doing as expected
                newfieldvalue.append(listitem.strip().replace('\n','').replace('\r',''))
            item = ';'.join(newfieldvalue).strip().lstrip(';').rstrip(';')

            c.execute("UPDATE {tn} SET {cn}=(:what) WHERE id=:nic".format(tn=table_name, cn=field[0]), {'what': item, 'nic': int(charity_num)})
            c.execute("UPDATE {tn} SET data_acquire_date=(:today) WHERE id=:nic".format(tn=table_name), {'today': date.today().strftime('%Y-%m-%d'), 'nic': int(charity_num)})
            conn.commit()
        print('updated entry for ' + charity_num)
    else:
        page.raise_for_status()

# query each charity html page
def query_charities(charity_nums, pairings):
    ## TODO insteading of using pairings from the global variable,
    ## get if from the get_fieldnames() function
    for ccnino in charity_nums[1:]:
        query = {'regId':ccnino,'subId':'0'}
        try:
            page = requests.get(url, params=query)
            scrape_write_data(ccnino, page, pairings)
        except requests.exceptions.Timeout:
            print('connection timed out: ' +  ccnino)
            errors.append(ccnino)
            continue
        except requests.exceptions.RequestException as e:
            print('Request Exception on ' + ccnino + ': ' + str(e))
            errors.append(ccnino)
            continue

def clean_fields():
    '''
    Some fields contain unwanted text coming from the XPath query
    TODO might it be better to do this action during the initial scraping?
    '''
    cleaning = [
        ("charity_number", "Charity no. ", ""),
        ("company_number", "Company no. ", ""),
        ("date_registered", "Date registered. ", ""),
        ("days_overdue", "Documents ", ""),
        ("days_overdue", " days overdue", "")
        ]
    
    for i in cleaning:
        c.execute('UPDATE {tn} SET {cn}=REPLACE({cn}, :tx, :replace)'.format(tn=table_name, cn=i[0]), {"tx": i[1], "replace": i[2]})
        conn.commit()


if __name__ == '__main__':
    url = "http://www.charitycommissionni.org.uk/charity-details"
    download_day = date.today().strftime('%Y%m%d')
    sqlite_file = 'data.sqlite' ## morph.io requirement
    table_name = 'data' ## morph.io requirement
    charity_nums = []
    errors = []
    pairings = get_fieldnames()

    conn = sqlite3.connect(sqlite_file)
    c = conn.cursor()

    set_up_table(table_name)
    get_charity_nums(charity_nums)
    get_fieldnames() ## TODO remove this once the query_charities function has been fixed
    query_charities(charity_nums, pairings)
    clean_fields()

    updated_today = c.execute("SELECT COUNT(*) FROM {tn} WHERE data_acquire_date=(:today)".format(tn='data'), {'today': date.today().strftime('%Y-%m-%d')})

    if len(errors) > 0:
        print('Data scraped from Charity Commission, except for these numbers:\n')
        for no in errors:
            print(no)
    else:
        print('Data scraped from Charity Commission for ' + str(updated_today.fetchone()[0]) + ' entries')

    conn.close()
