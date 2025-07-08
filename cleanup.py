### Clears out the game path after running create_pdf.py
import os

def delete_files():
    root_path = 'game'
    image_folders = ['front','back','double_sided']
    i = 0

    for folder_name in image_folders:
        working_path = os.path.join(root_path, folder_name)
        for item in os.listdir(working_path):
            full_path = os.path.join(working_path,item)
            if os.path.isfile(full_path):
                os.remove(full_path)
                print(f'Deleted {full_path}')
                i+=1
    

    print(f'Deleted {i} item{bool(i-1)*"s"}')

if __name__ == '__main__':
    delete_files()

