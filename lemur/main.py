import csv
import io

from puepy import Application, Page, t
from puepy.router import Router
from puepy.runtime import is_server_side, add_event_listener

from lemur.expensedb import Database

if not is_server_side:
    import js


class ExpenseLemurApp(Application):
    def initial(self):
        return {
            "loading": True,
        }

    def reload_db(self, save=True):
        self.state["known_people"] = (db.expense.get_unique_names(),)
        self.state["expenses"] = db.expense.select()
        self.state["summary"] = db.expense.summary()
        self.state["loading"] = False
        if save:
            self.local_storage["db"] = db.to_string()


app = ExpenseLemurApp()
existing_data = app.local_storage.get("db")
db = Database(existing_data)
app.reload_db(save=False)
app.install_router(Router, link_mode=Router.LINK_MODE_HASH)
app.local_storage.get("db")


@app.page("/")
class DefaultPage(Page):
    default_classes = ["flex", "flex-col", "flex-grow"]

    def initial(self):
        return {"import_error": None, "import_message": None}

    def populate(self):
        th_classes = "py-2 px-4 font-medium text-gray-500 uppercase tracking-wider"
        td_classes = "py-2 px-4 text-gray-700"

        if self.application.state["loading"]:
            with t.div(
                style="text-align: center; height: 100vh; display: flex; justify-content: center; align-items: center;"
            ):
                t.sl_spinner(style="font-size: 50px; --track-width: 10px;")
        else:
            with t.header(classes="flex justify-between items-center bg-white p-4 mb-4 shadow-lg"):
                t.sl_avatar(image="/img/icon/launchericon-512-512.png", label="Expense Lemur")

                t.h1(
                    " Expense Lemur",
                    classes="text-4xl font-bold",
                    style="color: rgb(149 96 40)",
                )

                with t.sl_dropdown(on_sl_select=self.on_menu_select):
                    t.sl_icon_button(name="gear", label="Settings", slot="trigger")
                    with t.sl_menu():
                        t.sl_menu_item(t.sl_icon(slot="prefix", name="box-arrow-down"), "Download CSV", value="export")
                        t.sl_menu_item(t.sl_icon(slot="prefix", name="upload"), "Import CSV", value="import")
                        t.sl_divider()
                        t.sl_menu_item(t.sl_icon(slot="prefix", name="x-circle"), "Clear All", value="clear_all")
                        t.sl_divider()
                        t.sl_menu_item(t.sl_icon(slot="prefix", name="info-lg"), "About", value="about")
            with t.main(classes="flex-grow container mx-auto p-4"):
                with t.div(classes="container mx-auto"):
                    if self.application.state["expenses"]:
                        with t.table(classes="table-auto w-full"):
                            t.thead(
                                t.tr(
                                    t.th("Owed By", classes=th_classes),
                                    t.th("Owed To", classes=th_classes),
                                    t.th("Description", classes=th_classes),
                                    t.th("Date/Amount", classes=th_classes),
                                    t.th(""),
                                ),
                            )
                            with t.tbody():
                                for expense in self.application.state["expenses"]:
                                    t.tr(
                                        t.td(expense["owed_from"], classes=td_classes),
                                        t.td(expense["owed_to"], classes=td_classes),
                                        t.td(expense["description"], classes=td_classes),
                                        t.td(
                                            expense["date_created"].strftime("%Y-%m-%d %H:%M %Z"),
                                            t.br(),
                                            t.sl_format_number(
                                                type="currency",
                                                currency="USD",
                                                value=str(expense["amount"]),
                                                lang="en-US",
                                                style="font-weight: bold",
                                            ),
                                            classes=td_classes,
                                        ),
                                        t.td(
                                            t.sl_button(
                                                t.sl_icon(name="trash3"),
                                                size="small",
                                                circle=True,
                                                data_id=expense["id"],
                                                on_click=self.on_delete_click,
                                            ),
                                            classes="text-right " + td_classes,
                                        ),
                                        classes="border-t border-gray-300",
                                    )
                    else:
                        with t.div(classes="bg-white p-6 rounded-lg shadow-lg"):
                            t.div("No expenses yet... Why not buy a coffee? ☕️", classes="text-center p-12 text-2xl")
                if self.application.state["summary"]:
                    t.br()
                    with t.div(classes="bg-white p-6 rounded-lg shadow-lg"):
                        with t.h2(classes="text-xl font-bold mb-6 text-center"):
                            t("Summary")
                        with t.table(classes="table-auto w-full"):
                            t.thead(t.tr(t.th("Payment"), t.th("Amount")))
                            with t.tbody():
                                for summary in self.application.state["summary"]:
                                    t.tr(
                                        t.td(summary["direction"]),
                                        t.td(
                                            t.sl_format_number(
                                                type="currency",
                                                currency="USD",
                                                value=str(summary["total_amount"]),
                                                lang="en-US",
                                            )
                                        ),
                                    )
                    t.br()
                    with t.div(classes="text-right"):
                        t.sl_button("Clear All", size="small", variant="text", on_click=self.on_show_clear_all_click)

            # Extra bottom padding. For mobile Safari, I couldn't figure out a better solution...
            t.br()
            t.br()
            t.br()
            with t.footer(classes="p-6"):
                t.sl_button(
                    "Add",
                    classes="w-full shadow-lg",
                    variant="primary",
                    size="large",
                    on_click=self.on_add_click,
                )

            self.populate_add_item_drawer()
            self.populate_clear_all_dialog()
            self.populate_export_dialog()
            self.populate_import_dialog()
            self.populate_about_dialog()

    def on_delete_click(self, event):
        db.expense.delete(id=event.currentTarget.getAttribute("data-id"))
        self.application.reload_db()

    def on_menu_select(self, event):
        if event.detail.item.value == "clear_all":
            self.refs["clear_all_dialog"].element.show()
        elif event.detail.item.value == "export":
            self.export_csv_file()
        elif event.detail.item.value == "import":
            self.refs["import_dialog"].element.show()
        elif event.detail.item.value == "about":
            self.refs["about_dialog"].element.show()
        else:
            print(f"Unknown menu item: {event.detail.item.value}")

    ##
    ## Add Item Drawer and Events
    ##
    def populate_add_item_drawer(self):
        with t.sl_drawer(ref="add_item_dialog", placement="bottom", label="Add Expense"):
            with t.form(id="iou-form", classes="space-y-4", on_submit=self.on_add_submit, ref="add_form"):
                with t.div(classes="flex"):
                    t.sl_input(label="From", classes="w-1/2 p-2", placeholder="Person who owes money", ref="from")
                    t.sl_input(label="To", classes="w-1/2 p-2", placeholder="Person who is owed money", ref="to")

                with t.div(classes="flex"):
                    t.sl_input(label="Amount", classes="w-1/4 p-2", type="number", ref="amount")
                    t.sl_input(label="Description", classes="w-3/4 p-2", ref="description")

                with t.sl_button(type="submit", variant="primary", classes="w-full"):
                    t("Save Expense")

    def on_add_submit(self, event):
        event.preventDefault()
        db.expense.insert_expense(
            amount=float(self.refs["amount"].element.value),
            description=self.refs["description"].element.value,
            owed_to=self.refs["to"].element.value,
            owed_from=self.refs["from"].element.value,
        )
        self.refs["add_item_dialog"].element.hide()
        self.refs["add_form"].element.reset()
        self.application.reload_db()

    def on_add_click(self, event):
        self.refs["add_item_dialog"].element.show()

    ##
    ## Clear all dialog and events
    ##
    def populate_clear_all_dialog(self):
        with t.sl_dialog(ref="clear_all_dialog", label="Clear All"):
            t("Are you sure you want to delete all transactions? This cannot be undone.")
            t.sl_button("Clear All", slot="footer", variant="warning", on_click=self.on_clear_all_click)
            t.sl_button("Cancel", slot="footer", variant="text", on_click=self.on_hide_clear_all_click)

    def on_clear_all_click(self, event):
        db.expense.delete()
        self.application.reload_db()
        self.refs["clear_all_dialog"].element.hide()

    def on_hide_clear_all_click(self, event):
        self.refs["clear_all_dialog"].element.hide()

    def on_show_clear_all_click(self, event):
        self.refs["clear_all_dialog"].element.show()

    ##
    ## Import dialog and events
    ##
    def populate_import_dialog(self):
        with t.sl_dialog(ref="import_dialog", label="Import CSV"):
            if self.state["import_message"]:
                with t.sl_alert(open=True):
                    t.sl_icon(name="info-circle")
                    t(" ", self.state["import_message"])
            else:
                t(
                    "This will import a CSV file of your expenses. The file should have columns for owed_from, owed_to,"
                    " description, amount, and date_created."
                )
                with t.form(on_submit=self.on_import_submit, ref="import_form"):
                    t.input(type="file", label="Select CSV file", ref="import_file", classes="p-4")
                    t.sl_checkbox("Clear existing data", ref="erase")
                if self.state["import_error"]:
                    with t.sl_alert(open=True, variant="danger"):
                        t.sl_icon(name="exclamation-triangle")
                        t(self.state["import_error"])
                t.sl_button(
                    "Import",
                    ref="import_submit",
                    slot="footer",
                    type="submit",
                    variant="primary",
                    on_click=self.on_import_submit,
                )
            t.sl_button(
                "Close", ref="import_close", slot="footer", variant="text", on_click=self.on_close_import_dialog_click
            )

    def on_close_import_dialog_click(self, event):
        event.preventDefault()
        self.refs["import_dialog"].element.hide()

    async def on_import_submit(self, event):
        event.preventDefault()
        with self.state.mutate():  # Wait on any changes till after we're done
            self.state["import_error"] = None
            self.state["import_message"] = None
            event.preventDefault()
            file = self.refs["import_file"].element.files.item(0)
            if not file:
                # self.state["import_error"] = "No file selected"
                return
            ab = await file.arrayBuffer()
            fd = io.StringIO(ab.to_bytes().decode("utf-8"))
            reader = csv.DictReader(fd)
            db.conn.execute("BEGIN TRANSACTION;")
            if self.refs["erase"].element.checked:
                db.conn.execute("DELETE FROM expense;")
            for i, row in enumerate(reader):
                try:
                    db.expense.insert_expense(
                        amount=float(row["amount"]),
                        description=row["description"],
                        owed_to=row["owed_to"],
                        owed_from=row["owed_from"],
                        date_created=row["date_created"],
                    )
                except KeyError:
                    self.state["import_error"] = f"Error on row {i+1}: Columns do not match expected columns"
                    db.conn.rollback()
                    return
                except (ValueError, TypeError):
                    self.state["import_error"] = f"Error on row {i+1}: Invalid data in row"
                    db.conn.rollback()
                    return
            self.application.reload_db()
            self.state["import_message"] = "Import successful"
            # self.refs["import_dialog"].element.hide()

    ##
    ## Download dialog and events
    ##

    def populate_export_dialog(self):
        with t.sl_dialog(ref="export_dialog", label="Download CSV"):
            t(
                "This will export a CSV file of your expenses, which you can open as a spreadsheet,"
                " share with friends, or import again to Expense Lemur."
            )
            if "export_url" in self.state:
                t.sl_button(
                    "Download",
                    slot="footer",
                    variant="primary",
                    href=self.state["export_url"],
                    download="expenses.csv",
                )
            else:
                t.sl_spinner()
            t.sl_button("Close", slot="footer", variant="text", on_click=self.on_close_export_dialog_click)

    def on_close_export_dialog_click(self, event):
        self.refs["export_dialog"].element.hide()

    def export_csv_file(self):
        field_names = ["owed_from", "owed_to", "description", "amount", "date_created"]

        f = io.StringIO()
        writer = csv.DictWriter(f, fieldnames=field_names)
        writer.writeheader()

        for row in self.application.state["expenses"]:
            writer.writerow({key: row[key] for key in field_names if key in row})

        # content = jsobj(f.getvalue())
        blob = js.Blob.new([f.getvalue()], {"type": "text/csv"})
        self.state["export_url"] = js.URL.createObjectURL(blob)

        self.refs["export_dialog"].element.show()

    ##
    ## About Dialog and events
    ##
    def populate_about_dialog(self):
        with t.sl_dialog(ref="about_dialog", label="Expense Lemur"):
            t.p("© Copyright 2024 Ken Kinder", classes="mb-4")
            t.div(
                """Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except 
            in compliance with the License. You may obtain a copy of the License at""",
                classes="mb-4",
            )
            t.p(
                t.a("http://www.apache.org/licenses/LICENSE-2.0", href="http://www.apache.org/licenses/LICENSE-2.0"),
                classes="mb-4 text-blue-500 hover:text-blue-700 underline",
            )
            t.p(
                "Unless required by applicable law or agreed to in writing, software distributed under the License is"
                ' distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or'
                " implied. See the License for the specific language governing permissions and limitations under"
                " the License.",
                classes="mb-4",
            )
            t.hr(classes="mb-4")
            t.p(
                "Expense Lemur is a simple app to track expenses between friends. It's a demo of ",
                t.a("PeuPy", href="https://puepy.dev/", classes="text-blue-500 hover:text-blue-700 underline"),
                " -- the reactive frontend framework for Python. See ",
                t.a(
                    "github.com/kkinder/expenselemur",
                    href="https://github.com/kkinder/expenselemur",
                    classes="text-blue-500 hover:text-blue-700 underline",
                ),
            )


if not is_server_side:
    from js import navigator, window

    if hasattr(navigator, "serviceWorker"):

        def onServiceWorkerError(err):
            print("service worker not registered", err)

        def onServiceWorkerDone(res):
            pass

        def loader(*args, **kwargs):
            navigator.serviceWorker.register("/serviceWorker.js").then(onServiceWorkerDone).catch(onServiceWorkerError)

        add_event_listener(window, "py:all-done", loader)

app.mount("#app")
