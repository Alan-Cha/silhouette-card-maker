---
title: 'Cutting Guide'
weight: 20
---

## Prerequisites

### Printer alignment

If you plan on having card backs and if you plan on making double faced cards, then you need to ensure that printer can print with good front and back alignment. Otherwise, your card fronts and backs may have an offset.

Your printer may have built-in tools for calibration and alignment adjustment. However, it doesn't, you can use [`offset_pdf.py`]({{% ref "../docs/offset.md" %}}) to compensate for the printer's offset.

### Cutting settings

Silhouette Studio provides a number of cutting settings, including **blade force**, **cutting speed**, **passes**, and **blade depth**.

![Cutting settings](/images/cutting_settings.png)

Before starting, determine the cutting settings that works best for you and the materials you want to cut.

To do this, first create a simple cutting template in Silhouette Studio. Then, set the blade force, cutting speed, and blade depth to something reasonable, but **set passes to 1**. You can have the machine recut again and again to determine the required passes. Change the settings as necessary.

![Simple cutting template](/images/cutting_template_simple.png)

The following is a table of working settings from various testers. Do not use these settings blindly. Test conservatively. If not, you risk breaking your machine or cutting through your mat.

| Machine      | Blade          | Card stock     | Lamination  | Force    | Speed | Passes | Depth |
| ------------ | -------------- | -------------- | ----------- | -------- | ----- | ------ | ----- |
| Cameo 5      | Autoblade      | 65 lb          | 3 mil       | 30       | 30    | 3      | 7     |
| Cameo 5      | Autoblade      | 65 lbs/250 gsm | 3 mil       | 30       | 20    | 4      | 7     |
| Cameo 5      | Autoblade      | 110 lb         | 3 mil       | 33       | 20    | 3      | 8     |
| Cameo 5      | Autoblade      | 110 lb/199 gsm | 3 mil       | 33       | 30    | 4      | 10    |
| Cameo 5      | Autoblade      | 220 gsm        | 150 microns | 30       | 26    | 4      | 8     |
| Cameo 5      | Autoblade      | 250 gsm        | 120 microns | 40       | 10    | 8      | 10    |
| Cameo 4 Plus | Autoblade      | 110 lb         | 3 mil       | 30       | 30    | 3      | 5     |
| Cameo 3      | Deep-Cut Blade | 110 lb         | 3 mil       | 33       | 5     | 5      | 19    |

## Instructions

Before starting, join our [Discord server](https://discord.gg/jhsKmAgbXc). If you have any questions, you can ask them in the `#troubleshooting` channel.

### Set up environment

[Install Silhouette Studio](https://www.silhouetteamerica.com/silhouette-studio).

Download the `silhouette-card-makers` code by cloning the [repo](https://github.com/Alan-Cha/silhouette-card-maker-testing) or clicking [here](https://github.com/Alan-Cha/silhouette-card-maker-testing/archive/refs/heads/main.zip). Unzip the code if necessary.

If you're on macOS or Linux, open **Terminal**. If you're on Windows, open **PowerShell**.

### Check if Python is installed

```sh
python --version
```

If it doesn't work, try `python3` as well. If that works, replace the following Python commands with `python3`.

If you don't have Python, install it by clicking [here](https://www.python.org/downloads/). In the installer, check the box to **"Add python.exe to PATH"**.

![Python installer](/images/python_installer.png)

After installation, close **Terminal**/**PowerShell**, reopen it, and verify again.

### Upgrade pip

```sh
python -m pip install --upgrade pip
```

### Navigate to the code

For the following command, replace `<path to the code>` with the file path to the code.

```sh
cd <path to the code>
```

> [!TIP]
> For example, if the code in the `Downloads` folder, then use the following:
> ```sh
> cd Downloads/silhouette-card-maker-testing-main/silhouette-card-maker-testing-main
> ```

### Create a Python virtual environment

A virtual environment ensures that the Python packages you install in the next step will not affect the rest of your computer.

Create a new virtual environment:

```sh
python -m venv venv
```

Then, activate the environment:

{{< tabs items="macOS/Linux,Windows" defaultIndex="1" >}}

  {{< tab >}}
```sh
. venv/bin/activate
```
  {{< /tab >}}
  {{< tab >}}
```powershell
.\venv\Scripts\Activate.ps1
```

> [!TIP]
> If you see a **security error**, run the following, then try activating the environment again.
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
> ```
  {{< /tab >}}

{{< /tabs >}}

You will know if the virtual environment has been activated when `(venv)` appears in the prompt.

### Install Python packages

```sh
pip install -r requirements.txt
```

### Create the PDF

Put card front images into the `game/front/` folder. Then, put a card back image into the `game/back/` folder.

> [!TIP]
> I've prepared the game, Zero sumZ, as an [example](https://github.com/Alan-Cha/silhouette-card-maker-testing/tree/main/examples/ZERO%20SUMZ). Simply move the assets to the appropriate image folders.
>
> You can also use a [plugin]({{% ref "../plugins" %}}) to populate the image folders. [Magic: The Gathering]({{% ref "../plugins/mtg.md" %}}), [Yu-Gi-Oh!]({{% ref "../plugins/yugioh.md" %}}), and [Lorcana]({{% ref "../plugins/lorcana.md" %}}) are currently supported.

Generate the PDF with the following:

```sh
python create_pdf.py
```

> [!TIP]
>`create_pdf.py` has many options such as **paper and card size** and **double-sided cards**. To learn more, see [here]({{% ref "../docs/create.md" %}}).

You can find the PDF in `game/output/game.pdf` and it should look similar to the following:

![PDF output](/images/create_pdf.png)

### Prepare the sheets

Print out the PDF and laminate the sheets.

> [!TIP]
> Because cardstock is thick, you may need to use a higher setting on your laminator. If not, you may have cloudy lamination and delamination issues.

### Cut the sheets

Open the `letter_standard_<version>.studio3` cutting template in Silhouette Studio. Cutting templates can be found in the [`cutting_templates/`](https://github.com/Alan-Cha/silhouette-card-maker-testing/tree/main/cutting_templates) folder.

![Cutting template](/images/cutting_template_standard.png)

Put a sheet on the cutting mat. The position of the sheet must match the cutting template. Note that for this template, the sheet must be in the **top left of the cutting mat grid**. Note that the **black square registration mark is the top left** as well.

![Sheet alignment](/images/sheet_alignment.jpg)

Use a Post-It note to **cover the bottom left card**. Because the card is so close to the bottom left L registration mark, the machine sometimes gets the two confused; covering the card will reduce registration issues. You can also use masking tape or a piece of paper with tape on it.

![Post-It note](/images/registration_fix.jpg)

Insert the mat into the machine. The left edge of the mat should be aligned with the notch on the machine. Then, click the media load button on the machine.

![Mat alignment](/images/mat_alignment.jpg)

Put your [cutting settings](#cutting-settings) into Silhouette Studio.

![Cutting settings](/images/cutting_template_settings.png)

Start the cutting job. Remember to remove the Post-It note after registration.

### Finish the cards

Click the media eject button on the machine to remove the mat.

Peel off the cards and remove the excess.

Because the cutting process may cause the card edges to delaminate, put the cards through the laminator a second time.

![Relaminating](/images/relamination.jpg)

Now you're ready to play with your cards!

## Next Steps

As mentioned, the `create_pdf.py` script offers many [configuration options]({{% ref "../docs/create.md" %}}). `create_pdf.py` can create double-sided cards, utilize different paper sizes, cut different card sizes, and more!

If you're interested in making proxies for TCGs, try using a [plugin]({{% ref "../plugins" %}}). For example, the [Magic: The Gathering plugin]({{% ref "../plugins/mtg.md" %}}) reads a decklist and automatically fetches card art.

Lastly, we have a [Discord server](https://discord.gg/jhsKmAgbXc)! We'd love to see you there! You can ask for help, share pictures, and chat with people who all love creating and playing card games.

Thanks for reading and best of luck with your card cutting adventures!