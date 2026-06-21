# Form Loader

Use the **Form Loader** to enter data for the current shift. 

The layout, fields, and Excel mapping of the Form Loader are determined by the
active form you select in the **Layout Manager**.

---

## Fields in the Standard Form

The default form includes the following fields:

### Shift Details (Header)
- **Date** & **Cast Date**
- **Bond** (Sand strength rating)
- **EFF %** (Shift efficiency)
- **Shift** (1st, 2nd, or 3rd)
- **Shift Hours** & **Target Time**
- **MTD %** (Month-to-date efficiency)
- **Goal MPH** (Target molds per hour)
- **Total Molds** (Total molds produced)
- **Ret North** & **Ret South** (Returns)
- **Start Time** & **End Time**

### Production Rows
- **Shop Order**: The manufacturing order number.
- **Part Number**: The ID of the part being run.
- **Rate**: The target molds per hour (filled in automatically).
- **Override**: A checkbox to manually change the rate.
- **Molds**: The number of molds produced.
- **Time**: The calculated time to run the molds.

### Downtime Rows
- **Start**: When the stoppage began.
- **Stop**: When the stoppage ended.
- **Code**: The numeric reason code for the downtime.
- **Cause**: A brief description of the problem.
- **Time**: The calculated minutes of downtime.

---

## Core Features and Tips

### Dynamic Rate Lookup
When you enter a **Part Number**, the app automatically looks up its standard rate
in the database and fills in the **Rate** column.

### Overriding a Rate
The **Rate** column is locked by default. If you need to enter a custom rate:
1. Check the **Override** box on that row.
2. Enter the custom rate.
3. Unchecking **Override** will lock the cell again and restore the standard rate.

### continuous Row Entry (Open-Row Behavior)
The tables always keep one empty row at the bottom. As soon as you start typing
in a user field (like **Shop Order** or **Start** time), a new blank row is
automatically added below it.

### Ghost Time (Footer)
The footer displays **Ghost Time**, which is the difference between your total
shift hours and the sum of your production and downtime.
- **Red**: Missing time (you need to log more production or downtime).
- **Green**: Extra time logged.

### Balancing Downtime
If you have missing time, click **Balance Downtime** in the footer. The app will
automatically distribute the missing minutes across your existing downtime rows
based on how long they lasted. If no downtime has been added yet, it will create
a new row for the adjustment.
> **Note:** If you have logged more time than your shift hours, you must remove
> or adjust downtime manually.

### Calculations and Saving
- Click **Calculate All** to update your efficiency numbers.
- Click **Save Draft** to save your progress. The app stores drafts safely in
  `data/pending`.
- Click **Save and Open** to write your current data into the Excel template and
  open it for review.
- Click **Print Last Export** to print the workbook.

---

## Excel Import & Export

- **Exporting**: Shift records are saved in your export folder, automatically
  organized into year and month folders (e.g., `2026/06 June`).
- **Importing**: You can load an existing Excel workbook back into the form.
  The app detects column locations and reconstructs downtime details.
