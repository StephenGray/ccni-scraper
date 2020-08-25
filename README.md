This is a scraper that runs on [Morph](https://morph.io). To get started [see the documentation](https://morph.io/documentation)

`scraper.py` downloads the daily charity register .csv file, and then scrapes extra information from the website for each charity in the register.

It queries information on each charity's page using XPath, as defined in `fields_xpath.txt`.

Table `data` is written to `data.sqlite` and contains all the information.