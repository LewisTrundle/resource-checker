import platform

SYSTEM_PLATFORM = platform.system()
RESOURCES = {
    "node": ["--version", "https://nodejs.org/en/"],
    #"npm": ["--version", "https://www.npmjs.com/"],
    #"Java": ["-version", "https://www.oracle.com/java/technologies/javase-jdk11-downloads.html"],
    #"Python": ["--version", "https://www.python.org/downloads/"],
    #"Git": ["--version", "https://git-scm.com/"],
    #"Hi": ["--version", "https://git-scm.com/"]
}
STANDARD_INSTALL_DIRS = [
    "C:\\Program Files",
    "C:\\Program Files (x86)",
    "C:\\Users\\*\\AppData\\Local",
    "/usr/bin",
    "/usr/local/bin",
    "/opt"
]