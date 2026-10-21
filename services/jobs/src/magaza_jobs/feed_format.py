"""Google Merchant (RSS 2.0, ``g:`` namespace) feed writer/reader.

Fields Merchant Center has no slot for (stock count, structured specs, complements, data sheet) are
carried in an extra ``ma:`` namespace, which Merchant Center ignores.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from urllib.parse import urlsplit

from magaza_core.contracts import Product, ProductSpec

G_NS = "http://base.google.com/ns/1.0"
MA_NS = "https://magaza-asistani.example/feed/1.0"
ET.register_namespace("g", G_NS)
ET.register_namespace("ma", MA_NS)


def _g(tag: str) -> str:
    return f"{{{G_NS}}}{tag}"


def _ma(tag: str) -> str:
    return f"{{{MA_NS}}}{tag}"


def _money(value: float) -> str:
    return f"{value:.2f} TRY"


def write_feed(products: list[Product], *, store_name: str, store_url: str) -> str:
    rss = ET.Element("rss", {"version": "2.0"})
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = store_name
    ET.SubElement(channel, "link").text = store_url
    ET.SubElement(channel, "description").text = f"{store_name} ürün feed'i"
    for p in products:
        item = ET.SubElement(channel, "item")

        def add(tag: str, text: str | None, item: ET.Element = item) -> None:
            if text is not None:
                ET.SubElement(item, tag).text = text

        add(_g("id"), p.sku)
        add(_g("title"), p.title)
        add(_g("description"), p.description)
        add(_g("link"), f"{store_url}{p.url}")
        add(_g("image_link"), f"{store_url}{p.image_url}")
        add(_g("availability"), "in_stock" if p.stock > 0 else "out_of_stock")
        if p.list_price and p.list_price > p.price:
            add(_g("price"), _money(p.list_price))
            add(_g("sale_price"), _money(p.price))
        else:
            add(_g("price"), _money(p.price))
        add(_g("brand"), p.brand)
        add(_g("condition"), "new")
        add(_g("identifier_exists"), "no")
        add(_g("product_type"), f"{p.category_name} > {p.subcategory}" if p.subcategory else p.category_name)
        for s in p.specs:
            detail = ET.SubElement(item, _g("product_detail"))
            ET.SubElement(detail, _g("section_name")).text = "Teknik"
            ET.SubElement(detail, _g("attribute_name")).text = s.label
            ET.SubElement(detail, _g("attribute_value")).text = (
                f"{s.value} {s.unit}" if s.unit else str(s.value)
            )
        add(_ma("category"), p.category)
        add(_ma("stock"), str(p.stock))
        add(_ma("unit"), p.unit)
        for s in p.specs:
            kind = (
                "bool"
                if isinstance(s.value, bool)
                else "number"
                if isinstance(s.value, int | float)
                else "string"
            )
            attrs = {"key": s.key, "label": s.label, "type": kind}
            if s.unit:
                attrs["unit"] = s.unit
            ET.SubElement(item, _ma("spec"), attrs).text = str(s.value)
        for tag in p.tags:
            add(_ma("tag"), tag)
        for sku in p.complement_skus:
            add(_ma("complement"), sku)
        add(_ma("doc_id"), p.doc_id)
        add(_ma("doc_url"), p.doc_url)
        add(_ma("rating"), None if p.rating is None else f"{p.rating:.1f}")
        add(_ma("review_count"), str(p.review_count or 0))
        add(_ma("sales_rank"), None if p.sales_rank is None else str(p.sales_rank))
        add(_ma("max_installments"), str(p.max_installments or 1))
        add(_ma("free_shipping"), "true" if p.free_shipping else "false")
    ET.indent(rss, space="  ")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(rss, encoding="unicode") + "\n"


def _path(url: str) -> str:
    parts = urlsplit(url)
    return parts.path if parts.scheme else url


def _price(text: str | None) -> float | None:
    return None if not text else float(text.split()[0])


def _spec_value(text: str, kind: str) -> str | float | bool:
    if kind == "bool":
        return text == "True" or text == "true"
    if kind == "number":
        number = float(text)
        return int(number) if number.is_integer() and "." not in text else number
    return text


def parse_feed(xml_text: str) -> list[Product]:
    root = ET.fromstring(xml_text)
    products: list[Product] = []
    for item in root.iter("item"):

        def text(tag: str, item: ET.Element = item) -> str | None:
            el = item.find(tag)
            return el.text if el is not None else None

        price, sale = _price(text(_g("price"))), _price(text(_g("sale_price")))
        product_type = (text(_g("product_type")) or "").split(" > ")
        stock_text = text(_ma("stock"))
        availability = text(_g("availability"))
        stock = int(stock_text) if stock_text is not None else (25 if availability == "in_stock" else 0)
        specs = [
            ProductSpec(
                key=el.get("key", ""),
                label=el.get("label", ""),
                unit=el.get("unit"),
                value=_spec_value(el.text or "", el.get("type", "string")),
            )
            for el in item.findall(_ma("spec"))
        ]
        rating, sales_rank = text(_ma("rating")), text(_ma("sales_rank"))
        products.append(
            Product(
                sku=text(_g("id")) or "",
                title=text(_g("title")) or "",
                brand=text(_g("brand")) or "",
                category=text(_ma("category")) or "genel",
                category_name=product_type[0] or "Genel",
                subcategory=product_type[1] if len(product_type) > 1 else None,
                description=text(_g("description")) or "",
                price=sale if sale is not None else (price or 0.0),
                list_price=price if sale is not None else None,
                currency="TRY",
                stock=stock,
                unit=text(_ma("unit")) or "adet",
                image_url=_path(text(_g("image_link")) or ""),
                url=_path(text(_g("link")) or ""),
                specs=specs,
                tags=[el.text or "" for el in item.findall(_ma("tag"))],
                complement_skus=[el.text or "" for el in item.findall(_ma("complement"))],
                doc_id=text(_ma("doc_id")),
                doc_url=text(_ma("doc_url")),
                rating=float(rating) if rating else None,
                review_count=int(text(_ma("review_count")) or 0),
                sales_rank=int(sales_rank) if sales_rank else None,
                max_installments=int(text(_ma("max_installments")) or 1),
                free_shipping=text(_ma("free_shipping")) == "true",
            )
        )
    return products
