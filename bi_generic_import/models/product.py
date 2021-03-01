# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

import time
import tempfile
import binascii
import xlrd
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from datetime import date, datetime
from openerp.exceptions import Warning
from openerp import models, fields, exceptions, api, _
import io

import logging

_logger = logging.getLogger(__name__)

try:
    import csv
except ImportError:
    _logger.debug("Cannot `import csv`.")
try:
    import xlwt
except ImportError:
    _logger.debug("Cannot `import xlwt`.")
try:
    import cStringIO
except ImportError:
    _logger.debug("Cannot `import cStringIO`.")
try:
    import base64
except ImportError:
    _logger.debug("Cannot `import base64`.")


class gen_product(models.TransientModel):
    _name = "gen.product"

    file = fields.Binary("File")
    import_option = fields.Selection(
        [("csv", "CSV File"), ("xls", "XLS File")], string="Select", default="csv"
    )
    product_option = fields.Selection(
        [("create", "Create Product"), ("update", "Update Product")],
        string="Option",
        required=True,
        default="create",
    )
    product_search = fields.Selection(
        [("by_code", "Search By Code"), ("by_name", "Search By Name")],
        string="Search Product",
    )

    @api.multi
    def create_product(self, values):
        product_obj = self.env["product.product"]
        product_categ_obj = self.env["product.category"]
        product_uom_obj = self.env["uom.uom"]
        if values.get("categ_id") == "":
            raise Warning("CATEGORY field can not be empty")
        else:
            categ_id = product_categ_obj.search([("name", "=", values.get("categ_id"))])

        if values.get("type") == "Consumable":
            type = "consu"
        elif values.get("type") == "Service":
            type = "service"
        elif values.get("type") == "Product":
            type = "product"

        if values.get("uom_id") == "":
            uom_id = 1
        else:
            uom_search_id = product_uom_obj.search([("name", "=", values.get("uom"))])
            uom_id = uom_search_id.id

        if values.get("uom_po_id") == "":
            uom_po_id = 1
        else:
            uom_po_search_id = product_uom_obj.search(
                [("name", "=", values.get("po_uom"))]
            )
            uom_po_id = uom_po_search_id.id
        if values.get("barcode") == "":
            barcode = False
        else:
            barcode = values.get("barcode")

        vals = {
            "name": values.get("name"),
            "default_code": values.get("default_code"),
            "categ_id": categ_id.id,
            "type": "product",
            "barcode": barcode,
            "uom_id": uom_id,
            "uom_po_id": uom_po_id,
            "lst_price": values.get("sale_price"),
            "standard_price": values.get("cost_price"),
            "weight": values.get("weight"),
            "volume": values.get("volume"),
        }
        res = product_obj.create(vals)
        return res

    @api.multi
    def import_product(self):

        if self.import_option == "csv":
            keys = [
                "name",
                "default_code",
                "categ_id",
                "type",
                "barcode",
                "uom",
                "po_uom",
                "sale_price",
                "cost_price",
                "weight",
                "volume",
            ]
            csv_data = base64.b64decode(self.file)
            data_file = io.StringIO(csv_data.decode("utf-8"))
            data_file.seek(0)
            file_reader = []
            res = {}
            csv_reader = csv.reader(data_file, delimiter=",")
            try:
                file_reader.extend(csv_reader)
            except Exception:
                raise exceptions.Warning(_("Invalid file!"))
            values = {}
            for i in range(len(file_reader)):
                #                val = {}
                field = list(map(str, file_reader[i]))
                values = dict(zip(keys, field))
                if values:
                    if i == 0:
                        continue
                    else:
                        values.update({"option": self.import_option})
                        if self.product_option == "create":
                            res = self.create_product(values)
                        else:
                            product_obj = self.env["product.product"]
                            product_categ_obj = self.env["product.category"]
                            product_uom_obj = self.env["product.uom"]
                            if values.get("categ_id") == "":
                                raise Warning("CATEGORY field can not be empty")
                            else:
                                categ_id = product_categ_obj.search(
                                    [("name", "=", values.get("categ_id"))]
                                )
                            if values.get("type") == "Consumable":
                                type = "consu"
                            elif values.get("type") == "Service":
                                type = "service"
                            elif values.get("type") == "Stockable Product":
                                type = "product"

                            if values.get("uom_id") == "":
                                uom_id = 1
                            else:
                                uom_search_id = product_uom_obj.search(
                                    [("name", "=", values.get("uom"))]
                                )
                                uom_id = uom_search_id.id

                            if values.get("uom_po_id") == "":
                                uom_po_id = 1
                            else:
                                uom_po_search_id = product_uom_obj.search(
                                    [("name", "=", values.get("po_uom"))]
                                )
                                uom_po_id = uom_po_search_id.id
                            if values.get("barcode") == "":
                                barcode = False
                            else:
                                barcode = values.get("barcode")

                            if self.product_search == "by_code":
                                product_ids = self.env["product.product"].search(
                                    [("default_code", "=", values.get("default_code"))]
                                )
                                if product_ids:
                                    product_ids.write(
                                        {
                                            "name": values.get("name"),
                                            #'default_code':values.get('default_code'),
                                            "categ_id": categ_id.id,
                                            "type": "product",
                                            "barcode": barcode,
                                            "uom_id": uom_id,
                                            "uom_po_id": uom_po_id,
                                            "lst_price": values.get("sale_price"),
                                            "standard_price": values.get("cost_price"),
                                            "weight": values.get("weight"),
                                            "volume": values.get("volume"),
                                        }
                                    )
                                else:
                                    raise Warning(
                                        _('"%s" Product not found.')
                                        % values.get("default_code")
                                    )
                            else:
                                product_ids = self.env["product.product"].search(
                                    [("name", "=", values.get("name"))]
                                )
                                if product_ids:
                                    product_ids.write(
                                        {  #'name':values.get('name'),
                                            "default_code": values.get("default_code"),
                                            "categ_id": categ_id.id,
                                            "type": "product",
                                            "barcode": barcode,
                                            "uom_id": uom_id,
                                            "uom_po_id": uom_po_id,
                                            "lst_price": values.get("sale_price"),
                                            "standard_price": values.get("cost_price"),
                                            "weight": values.get("weight"),
                                            "volume": values.get("volume"),
                                        }
                                    )
                                else:
                                    raise Warning(
                                        _("%s product not found.") % values.get("name")
                                    )
        else:
            fp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
            fp.write(binascii.a2b_base64(self.file))
            fp.seek(0)
            values = {}
            res = {}
            workbook = xlrd.open_workbook(fp.name)
            sheet = workbook.sheet_by_index(0)
            for row_no in range(sheet.nrows):
                val = {}
                if row_no <= 0:
                    fields = map(
                        lambda row: row.value.encode("utf-8"), sheet.row(row_no)
                    )
                else:
                    line = list(
                        map(
                            lambda row: isinstance(row.value, bytes)
                            and row.value.encode("utf-8")
                            or str(row.value),
                            sheet.row(row_no),
                        )
                    )
                    if self.product_option == "create":
                        values.update(
                            {
                                "name": line[0],
                                "default_code": line[1],
                                "categ_id": line[2],
                                "type": line[3],
                                "barcode": line[4],
                                "uom": line[5],
                                "po_uom": line[6],
                                "sale_price": line[7],
                                "cost_price": line[8],
                                "weight": line[9],
                                "volume": line[10],
                            }
                        )
                        res = self.create_product(values)
                    else:
                        product_obj = self.env["product.product"]
                        product_categ_obj = self.env["product.category"]
                        product_uom_obj = self.env["product.uom"]
                        if line[2] == "":
                            raise Warning("CATEGORY field can not be empty")
                        else:
                            categ_id = product_categ_obj.search(
                                [("name", "=", line[2])]
                            )
                        if line[3] == "Consumable":
                            type = "consu"
                        elif line[3] == "Service":
                            type = "service"
                        elif line[3] == "Stockable Product":
                            type = "product"

                        if line[5] == "":
                            uom_id = 1
                        else:
                            uom_search_id = product_uom_obj.search(
                                [("name", "=", line[5])]
                            )
                            uom_id = uom_search_id.id

                        if line[6] == "":
                            uom_po_id = 1
                        else:
                            uom_po_search_id = product_uom_obj.search(
                                [("name", "=", line[6])]
                            )
                            uom_po_id = uom_po_search_id.id
                        if line[4] == "":
                            barcode = False
                        else:
                            barcode = line[4]

                        if self.product_search == "by_code":
                            product_ids = self.env["product.product"].search(
                                [("default_code", "=", line[1])]
                            )
                            if product_ids:
                                product_ids.write(
                                    {
                                        "name": line[0],
                                        #'default_code': line[1],
                                        "categ_id": categ_id.id,
                                        "type": "product",
                                        "barcode": barcode,
                                        "uom_id": uom_id,
                                        "uom_po_id": uom_po_id,
                                        "lst_price": line[7],
                                        "standard_price": line[8],
                                        "weight": line[9],
                                        "volume": line[10],
                                    }
                                )
                            else:
                                raise Warning(_('"%s" Product not found.') % line[1])
                        else:
                            product_ids = self.env["product.product"].search(
                                [("name", "=", line[0])]
                            )
                            if product_ids:
                                product_ids.write(
                                    {  #'name':line[0],
                                        "default_code": line[1],
                                        "categ_id": categ_id.id,
                                        "type": "product",
                                        "barcode": barcode,
                                        "uom_id": uom_id,
                                        "uom_po_id": uom_po_id,
                                        "lst_price": line[7],
                                        "standard_price": line[8],
                                        "weight": line[9],
                                        "volume": line[10],
                                    }
                                )
                            else:
                                raise Warning(_("%s product not found.") % line[0])

        return res
