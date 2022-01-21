'''
Простой сприпт для конвертации jpg в heic файлов.
При первом запуске скрипт создаст необходимые директории.
Затем файлы eps скопируйте в папку input и запустите скрипт
Дождитесь окончания результата. Сконвертированные файлы находятся в папке output
'''

from datetime import datetime
from zipfile import ZipFile
import os
import threading
import tempfile
import subprocess

from multiprocessing.pool import ThreadPool


class ConsoleProgressBar:
    """
    https://stackoverflow.com/questions/3173320/text-progress-bar-in-the-console
    """

    def __init__(self, total):
        self.total = total
        self.iteration = -1
        self.add_progress()

    def add_progress(self):
        self._printProgressBar()

    # Print iterations progress
    def _printProgressBar(self, prefix='', suffix='', decimals=1, length=100, fill='█', printEnd="\r"):
        """
        Call in a loop to create terminal progress bar
        @params:
            iteration   - Required  : current iteration (Int)
            total       - Required  : total iterations (Int)
            prefix      - Optional  : prefix string (Str)
            suffix      - Optional  : suffix string (Str)
            decimals    - Optional  : positive number of decimals in percent complete (Int)
            length      - Optional  : character length of bar (Int)
            fill        - Optional  : bar fill character (Str)
            printEnd    - Optional  : end character (e.g. "\r", "\r\n") (Str)
        """

        self.iteration += 1
        percent = ("{0:." + str(decimals) + "f}").format(100 * (self.iteration / float(self.total)))
        filledLength = int(length * self.iteration // self.total)
        bar = fill * filledLength + '-' * (length - filledLength)
        print(f'\r{prefix} |{bar}| {percent}% {suffix}', end=printEnd)
        # Print New Line on Complete
        if self.iteration == self.total:
            print()

def extract_zip(input_zip):
    """Extract zip to RAM memory and return eps files list"""
    input_zip = ZipFile(input_zip)

    # List eps files from zip
    zip_files_list = []

    for name in input_zip.namelist():
        if is_file_extension(name):
            zip_files_list.append(input_zip.read(name))
    return zip_files_list


def is_file_extension(file_name, extension=".jpg"):
    """Check if file extension *.eps or other if set"""
    filename, file_extension = os.path.splitext(file_name)
    return file_extension.lower() == extension


def save_data(file, out_folder, progress):
    global threadLock

    # https://github.com/strukturag/libheif
    heic_file_name = get_file_name(file)[:-4] + ".HEIC"
    path_heic_file = os.path.join(out_folder, heic_file_name)

    cmd_to_hevic = '"{heif_enc}" "{input}" -o "{output}"'
    cmd_to_hevic = cmd_to_hevic.format(heif_enc= os.path.join(os.getcwd(),"tools", "heif-enc.exe"),
                                       input=file,
                                       output=path_heic_file)
    # https://exiftool.org/index.html
    cmd_to_metadata = '"{exiftool}" -overwrite_original -tagsFromFile "{input}" -all:all "{output}"'
    cmd_to_metadata = cmd_to_metadata.format(exiftool=os.path.join(os.getcwd(),"tools", "exiftool.exe"),
                                             input=file,
                                             output=path_heic_file)
    #print(cmd_to_metadata)
    s = subprocess.Popen(cmd_to_hevic + " && " + cmd_to_metadata, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         shell=True)
    s.wait()

    threadLock.acquire()
    progress.add_progress()
    threadLock.release()


def find_jpg_files(path_to_folder):
    files_list = []

    for file in os.listdir(path_to_folder):
        if is_file_extension(file):
            files_list.append(os.path.join(path_to_folder,file))
    return files_list


def find_files_folder(path):
    """
    Find files and folder that will be user to extract data
    :param path: path to filder where stored files to extract
    :return: list with full path to file or folder
    """
    temp_list = []
    for file in os.listdir(path):
        full_path = os.path.join(path, file)

        if os.path.isdir(full_path):
            temp_list.append(full_path)
        else:
            if os.path.isfile(full_path) and is_file_extension(file, ".zip"):
                temp_list.append(os.path.join(full_path))

    # Also search eps files in root folder
    temp_list.append(path)

    return temp_list


def create_pool(files_list, output_file_path):
    """
    files_list - full path to file
    output_file - file where save extracted data

    """
    if len(files_list) == 0:
        print()
        print(f"Файлы *.jpg не найдены в '{get_file_name(path)}'")
        return

    if os.path.exists(output_file_path):
        print("Папка уже существует", get_file_name(output_file_path))
        #return
        #os.remove(output_file_path)
    else:
        os.mkdir(output_file_path)



    print()
    print(f"Обрабатываем '{get_file_name(path)}' файлов {len(files_list)}")

    pool = ThreadPool(processes=8)
    progress = ConsoleProgressBar(len(files_list))

    for file in files_list:
        pool.apply_async(save_data, args=(file, output_file_path, progress))
    pool.close()
    pool.join()

def get_file_name(path):
    return os.path.basename(os.path.normpath(path))

if __name__ == '__main__':

    threadLock = threading.Lock()

    # Путь до текущей дериктории
    path = os.path.dirname(__file__)

    # Создать папки для файлов, если они отсуствуют
    for folder in ('input', 'output'):
        if not os.path.isdir(folder):
            os.mkdir(folder)
            print("Папки input и output созданы. Добавьте файлы eps со штрихкодами в папку input и перезапустите скрипт.")

    # Путь до папки с eps штрихкодами
    pathin = os.path.join(path, 'input')
    pathout = os.path.join(path, 'output')

    start_time = datetime.now()

    # Contains files or folder to extract data
    file_folder_list = find_files_folder(pathin)

    print("Найдены файлы и папки:")
    print(file_folder_list)

    for path in file_folder_list:

        if os.path.isdir(path):
            input_files = find_jpg_files(path)
            create_pool(input_files, os.path.join(pathout, get_file_name(path)))

        if os.path.isfile(path):
            # Create temp dir to extract .zip
            with tempfile.TemporaryDirectory() as tmpdirname:
                with ZipFile(path, 'r') as zipObj:
                    zipObj.extractall(tmpdirname)
                    input_files = find_jpg_files(tmpdirname)
                    create_pool(input_files, os.path.join(pathout, get_file_name(path)))

    print()
    print("Завершено за", datetime.now() - start_time)
