# This script summarize the expenses and incomes.
import json
from anytree.importer import JsonImporter
from anytree import PreOrderIter, PostOrderIter
from pint import UnitRegistry
from expense_functions import expense_string, valid_input
import matplotlib.pyplot as plt
from expense_module import ExpenseEntry, IncomeEntry
import datetime


ureg = UnitRegistry()
Q_ = ureg.Quantity


try:  # Load the expense list, income list and categories.
    with open("my_expenses.json", "r") as f:
        expense_list_data = json.load(f)
    expense_list = [ExpenseEntry(**entry) for entry in expense_list_data]

    with open("my_incomes.json", "r") as f:
        income_list_data = json.load(f)

    income_list = [IncomeEntry(**entry) for entry in income_list_data]

    importer = JsonImporter()
    with open("expense_categories.json", "r") as f:
        expense_type = importer.read(f)

    with open("income_categories.json", "r") as f:
        income_type = importer.read(f)
except FileNotFoundError:
    print("Please run initialize_data.py first")
else:
    # Choose the time range to summarize.
    message = "What range fo date do you want to summarize? 1. All time, 2. Specific month (Please enter a number): "
    time_range = valid_input(message, ["1", "2"])

    # Select the month to summarize.
    if time_range == "2":
        # Figure out the options of year.
        year_list = []
        for entry in expense_list:
            date = datetime.date.fromisoformat(entry.date)
            year_list.append(date.year)

        year_list = list(set(year_list))
        year_list.sort()

        # Figure out the options of month.
        month_list = []  # Store year in month in (year * 100 + month) integer format.
        for entry in expense_list:
            date = datetime.date.fromisoformat(entry.date)
            for year in year_list:
                if date.year == year:
                    month_list.append(year * 100 + date.month)

        month_list = list(set(month_list))
        month_list.sort()

        # Ask which month to summarize.
        message = "Please select a month. "
        i = 0
        for month in month_list:
            i += 1
            message += str(i) + ". " + str(month % 100) + "/" + str(month // 100) + " "

        message += "(Please enter a number): "

        valid_response = False
        while not valid_response:
            month_selected = input(message)
            if month_selected in [str(x) for x in range(1, i + 1)]:
                valid_response = True
                month = month_list[int(month_selected) - 1] % 100
                year = month_list[int(month_selected) - 1] // 100
            else:
                print("Invalid option.")

        # Remove all other entries from the list.
        new_expense_list = []
        for entry in expense_list:
            date = datetime.date.fromisoformat(entry.date)
            if date.month == month and date.year == year:
                new_expense_list.append(entry)

        expense_list = new_expense_list

        new_income_list = []
        for entry in income_list:
            date = datetime.date.fromisoformat(entry.date)
            if date.month == month and date.year == year:
                new_income_list.append(entry)

        income_list = new_income_list

        plot_title = "Monthly Summary: " + str(month) + "/" + str(year)

    else:
        plot_title = "All Time Summary"

    # Sum the spending at the last child level.
    for category in PreOrderIter(expense_type):
        setattr(category, "total", 0)
        setattr(category, "total_regular", 0)
        setattr(category, "total_irregular", 0)
        i = 0
        for entry in expense_list:
            if category.name == entry.category:
                category.total += entry.cost
                if entry.regular:
                    category.total_regular += entry.cost
                else:
                    category.total_irregular += entry.cost

            i += 1

    # Sum the spending of subcategories into categories.
    for category in PostOrderIter(expense_type):
        for child in category.children:
            category.total += child.total
            category.total_regular += child.total_regular
            category.total_irregular += child.total_irregular

    for category in PreOrderIter(expense_type):
        category.total = round(category.total, 2)
        category.total_regular = round(category.total_regular, 2)
        category.total_irregular = round(category.total_irregular, 2)

    print("Total spending in each category:")

    for category in PreOrderIter(expense_type):
        print(f"{len(category.ancestors) * '   '}{category.name}: ${category.total}")

    print("-" * 100)
    # Sum the income at the last child level.
    for category in PreOrderIter(income_type):
        setattr(category, "total", 0)
        for entry in income_list:
            if category.name == entry.category:
                category.total += entry.amount

    # Sum the income of subcategories into categories.
    for category in PostOrderIter(income_type):
        for child in category.children:
            category.total += child.total

    for category in PreOrderIter(income_type):
        category.total = round(category.total, 2)

    print("Total earning in each type of income:")

    for category in PreOrderIter(income_type):
        print(f"{len(category.ancestors) * '   '}{category.name}: ${category.total}")

    # Compare price if quantity (weight) is noted.
    for category in PostOrderIter(expense_type):
        if "quantity (weight)" in category.notes:
            print("-" * 100)
            cheapest_per_lb = -1
            most_expensive = 0
            total_weight = 0
            total_cost = 0
            i = -1
            for entry in expense_list:
                i += 1
                if entry.category == category.name:
                    weight_in_lb = Q_(entry.notes["quantity (weight)"]).to("lb")
                    price_per_lb = entry.cost / weight_in_lb.magnitude
                    total_weight += weight_in_lb.magnitude
                    total_cost += entry.cost
                    if cheapest_per_lb < 0 or price_per_lb < cheapest_per_lb:
                        cheapest_per_lb = price_per_lb
                        cheapest_index = i
                    if price_per_lb > most_expensive:
                        most_expensive = price_per_lb
                        most_expensive_index = i
            try:
                print(
                    f"The cheapest {category.name} is: ${round(cheapest_per_lb, 2)} per pound, with the following purchase:"
                )
                entry = expense_list[cheapest_index]
                print(expense_string(entry))
                print(
                    f"The most expensive {category.name}  is: ${round(most_expensive, 2)} per pound, with the following purchase:"
                )
                entry = expense_list[most_expensive_index]
                print(expense_string(entry))
                print(
                    f"You bought {round(total_weight, 1)} lb of {category.name} in total, ${round(total_cost / total_weight, 2)} per pound on average."
                )
                print(
                    f"You can save ${round(total_cost - cheapest_per_lb * total_weight, 2)} if you stick with the cheapest option."
                )
            except NameError:
                print(f"No {category.name} was bought.")

    # Draw the pie charts.
    values = [expense_type.total_regular, expense_type.total_irregular]

    figure, axes = plt.subplots(1, 3)

    try:
        axes[1].pie(values, autopct="%1.1f%%", startangle=90)
        axes[1].set_title(f"Total Spending\n${expense_type.total}")
    except ValueError:
        print("There are no expenses to plot.")

    regular_category = []
    regular_value = []
    for child in expense_type.children:
        if child.total_regular > 0:
            regular_category.append(child.name + f" ${child.total_regular}")
            regular_value.append(child.total_regular)

    try:
        axes[0].pie(
            regular_value, labels=regular_category, autopct="%1.1f%%", startangle=180
        )
        axes[0].set_title(f"Regular ${expense_type.total_regular}")
    except ValueError:
        print("There are no regular expense.")

    irregular_category = []
    irregular_value = []
    for child in expense_type.children:
        if child.total_irregular > 0:
            irregular_category.append(child.name + f" ${child.total_irregular}")
            irregular_value.append(child.total_irregular)

    try:
        axes[2].pie(irregular_value, labels=irregular_category, autopct="%1.1f%%")
        axes[2].set_title(f"Irregular ${expense_type.total_irregular}")
    except ValueError:
        print("No irregular expanse.")

    figure.suptitle(plot_title)

    plt.show()
