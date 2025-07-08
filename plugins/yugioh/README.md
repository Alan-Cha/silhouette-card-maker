# Yugioh Plugin

This plugin reads a decklist, fetches card art from [ygoprodeck](https://ygoprodeck.com/card-database/?num=24&offset=0), and puts them in the proper `game/` directories.

This plugin supports the following decklist formats: `ydk`, `ydke`. To learn more, see [here](#formats).

## Basic instructions

Navigate to the [root directory](../..). This plugin is not meant to be run in `plugins/yugioh/`.

If you're on macOS or Linux, open **Terminal**. If you're on Windows, open **PowerShell**.

Create and start your virtual Python environment and install Python dependencies if you have not done so already. See [here](../../README.md#basic-instructions) for more information.

Put your decklist into a text file in `game/decklist`. In this example, the filename is `deck.ydk` and the decklist format is YDK (`ydk`).

Run the script.

```sh
python plugins/yugioh/fetch.py game/decklist/deck.ydk ydk
```

Now you can create the PDF using [`create_pdf.py`](../../README.md#create_pdfpy).

## Usage

### YDK
YDK decklists can be stored in either `.ydk` or `.txt` files. For more information on the format, see the Format To learn more about the format, see [here](#formats).

```sh
python plugins/yugioh/fetch.py game/decklist/deck.ydk ydk
```

### YDKe

YDKe decklists can be directly pasted into the Command Line as long as they are wrapped in quotes. The following example uses the YDKe decklist:

```
ydke://CDfpAQg36QGBAyEEgQMhBOcqwwXnKsMFSIA/AUiAPwFIgD8B/s84AJuTywGbk8sBm5PLATUHgwI1B4MCNQeDAv2JnAX9iZwF/YmcBdcanwGglAQCE0dlADm+EgQ5vhIE/fqRBYv9YwAQLRoCEC0aAhAtGgIeN4IBPqRxAf4KgAQiSJkAIkiZACJImQBL8mcCS/JnAkvyZwIkQTwBNlmlBQ==!tGFNAfmCDgQUh7AFmBskA45gkQMm1FgAQvNMAGlM5gWNJ5gDSw97ATI1VQLERCEFqRp+AMoavwGS+pQA!reIKAq3iCgKt4goCRK0EBUStBAVErQQF+9wUAUO+3QBDvt0AtYgRALWIEQC1iBEAkvrlAWaDAgCc4b0A!
```

Example

```sh 
python plugins/yugioh/fetch.py "ydke://CDfpAQg36QGBAyEEgQMhBOcqwwXnKsMFSIA/AUiAPwFIgD8B/s84AJuTywGbk8sBm5PLATUHgwI1B4MCNQeDAv2JnAX9iZwF/YmcBdcanwGglAQCE0dlADm+EgQ5vhIE/fqRBYv9YwAQLRoCEC0aAhAtGgIeN4IBPqRxAf4KgAQiSJkAIkiZACJImQBL8mcCS/JnAkvyZwIkQTwBNlmlBQ==!tGFNAfmCDgQUh7AFmBskA45gkQMm1FgAQvNMAGlM5gWNJ5gDSw97ATI1VQLERCEFqRp+AMoavwGS+pQA!reIKAq3iCgKt4goCRK0EBUStBAVErQQF+9wUAUO+3QBDvt0AtYgRALWIEQC1iBEAkvrlAWaDAgCc4b0A!" ydke 
```

YDKe can also be stored in a `.txt` without needing quotes. 

Example:

```
python plugins/yugioh/fetch.py game/decklist/deck.txt ydke
```

To learn more about the format, see [here](#formats).

## Formats

### YDK

`ydk` is the file format used by [ygoprodeck](https://ygoprodeck.com/) and edopro. Decklist files can end in `.txt` or `.ydk` extensions. YDK format is of the following structure: 

```
#main
[card passcode]
...
#extra
[card passcode]
...
!side
[card passcode]
...

```

Example:

```
#main 
91073013
92895501
92895501
92895501
9091064
9091064
9091064
91025875
92248362
#extra 
90448279
90303227
61374414
64276752
!side 
27204311
27204311
82385847
```

### YDKe

`ydke` is a compressed version of `ydk` that allows decks to be easily imported or exported into YGO Omega, edopro, or [ygoprodeck](https://ygoprodeck.com/) via copy/paste. These are typically long strings beginning with `ydke://` and are of the form:

```
ydke://[main]![extra]![side]!
``` 

Example:

```
ydke://CDfpAQg36QGBAyEEgQMhBOcqwwXnKsMFSIA/AUiAPwFIgD8B/s84AJuTywGbk8sBm5PLATUHgwI1B4MCNQeDAv2JnAX9iZwF/YmcBdcanwGglAQCE0dlADm+EgQ5vhIE/fqRBYv9YwAQLRoCEC0aAhAtGgIeN4IBPqRxAf4KgAQiSJkAIkiZACJImQBL8mcCS/JnAkvyZwIkQTwBNlmlBQ==!tGFNAfmCDgQUh7AFmBskA45gkQMm1FgAQvNMAGlM5gWNJ5gDSw97ATI1VQLERCEFqRp+AMoavwGS+pQA!reIKAq3iCgKt4goCRK0EBUStBAVErQQF+9wUAUO+3QBDvt0AtYgRALWIEQC1iBEAkvrlAWaDAgCc4b0A!
```
