# parsedBible
This open-source repository contains examples of parsed Bible revisions in JSON format. The structure of the repository includes a revision control file and a directory for each revision.
## Structure
For each revision, there are two main elements: a revision control file and a directory that contains parsed JSON files.

### Revision Control File 
This is a JSON file that contains a list of documents, one for every book-chapter occurrence, with the number of verses in that chapter.

Example:
```json
[
    {
        "book": "1ch",
        "chapter": "20",
        "verses": 31
    },
    ...
]
```

### Revision directory
This is a directory with an uppercase name that contains a set of subfolders. Each subfolder keeps JSON files related to a book, and has a name with the format `([0-9]{2})_([0-9a-z]{3})`, where the first part is a book order index and the second part is the book abbreviation.

### Book-chapter json files
Each book-chapter JSON file contains information about a specific chapter, and has a name with the format `([0-9a-z]{3})\.([0-9]{3})\.json`, where the first part is the book abbreviation, and the second part is the chapter number.
#### Example of json content of jud.001.json
```json
{
    "book": "JUD",
    "rev": "RVR60",
    "chapter": "1",
    "verses": [
        {
            "verse": "1",
            "text": "Judas,  siervo de Jesucristo, y hermano de Jacobo, a los llamados, santificados en Dios Padre, y guardados en Jesucristo: \n",
            "readableText": "Judas, siervo de Jesucristo, y hermano de Jacobo, a los llamados, santificados\nen Dios Padre, y guardados en Jesucristo:\n\n"
        },
        ...
    ]
}
```

