import gspread, time

def extract_promts(sheet):
    def make_dict(arrays):
        dict = {array[0] : array[1:] for array in arrays}
        for key in dict.keys():
            if key == 'inline buttons':
                # all cell are in format text: ..., call_back = ...
                # that are neccessary for the buttons
                array = []
                for button in dict[key]:
                    if button != '':
                        array.append({text.split(':')[0] : text.split(':')[1] for text in button.split('; ')})

                dict[key] = array
        return dict

    data = sheet.get_all_values()
    filtered_data = [[row[0]] + [cell for cell in row[1:] if cell != ''] for row in data]
    promts = {}
    key = None
    for row_num in range(len(filtered_data)):
        row = filtered_data[row_num]
        # if empty ->add to previous key
        if row[0] != '':
            key = row[0]
            promts[key] = []
        promts[key] += [row[1:]]
    return {key : make_dict(promts[key]) for key in promts.keys()}

# add credentials to the account
gc = gspread.service_account(filename='lore-420220.json')

# add bot
sheet = gc.open("LORE")
orders = {}

# get the scores sheet of the Spreadsheet
score_sheet = sheet.worksheet('scores')
promt_sheet = sheet.worksheet('promts')

promt_file = 'promts.txt'
while True:
    with open(promt_file, 'w') as file:
        # file.clear()
        data = promt_sheet.get_all_values()
        for row in range(len(data)):
            file.write('/cell'.join(data[row]))
            if row != len(data) - 1: file.write('/row')
    
        file.close()
    time.sleep(1)