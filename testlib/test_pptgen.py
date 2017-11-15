# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import random
import numpy as np
import pandas as pd
from pptx import Presentation
from unittest import TestCase
from nose.tools import eq_, ok_
from . import folder, sales_file
from gramex.pptgen import pptgen
from pptx.enum.text import PP_ALIGN
from nose.tools import assert_raises
from orderedattrdict import AttrDict
from tornado.template import Template
from tornado.escape import to_unicode
from pptx.shapes.shapetree import SlideShapes
from pandas.util.testing import assert_frame_equal
from pptx.enum.shapes import MSO_SHAPE, MSO_SHAPE_TYPE


class TestPPTGen(TestCase):
    # Test Case module for pptgen

    @classmethod
    def setUp(cls):
        # Setup class method to initialize common variables.
        cls.input = os.path.join(folder, 'input.pptx')
        cls.output = os.path.join(folder, 'output.pptx')
        cls.image = os.path.join(folder, 'small-image.jpg')
        cls.data = pd.read_excel(sales_file, encoding='utf-8')
        if os.path.exists(cls.output):
            os.remove(cls.output)

    def template(self, tmpl, data):
        # Function to generate tornado template.
        return to_unicode(Template(tmpl, autoescape=None).generate(**data))

    def get_shape(self, target, name):
        # Function to return required shape.
        return [shape for shape in target.slides[0].shapes if shape.name == name]

    def draw_chart(self, slidenumber, data, rule):
        # Function to change data in pptx native charts.
        return pptgen(
            source=self.input,
            only=slidenumber,
            data={'data': data},
            edit_chart=rule)

    def check_if_number(self, data):
        # Function to check if data is a number
        decimal_points = 6
        try:
            return round(float(data), decimal_points)
        except TypeError:
            return data

    def check_chart(self, shape, data, series):
        # Function to validata pptx-native charts updated data.
        # Chart shape must have `chart_type` attribute
        ok_(hasattr(shape.chart, 'chart_type'))
        # Chart series name nust be from selected columns
        eq_(sorted([_series.name for _series in shape.chart.series]), series)
        for _series in shape.chart.series:
            datapints = [self.check_if_number(point) for point in data[_series.name].tolist()]
            seriesvals = [self.check_if_number(point) for point in list(_series.values)]
            eq_(datapints, seriesvals)

    def test_data_format(self):
        # Testing data section. Data argument must be a `dict` like object
        with assert_raises(ValueError):
            pptgen(source=self.input, only=1, data=[1, 2])
        pptgen(source=self.input, only=1, data={})
        pptgen(source=self.input, only=1, data={'data': [1, 2, 3]})

    def test_source_without_target(self):
        # Test case to compare no change.
        target = pptgen(source=self.input, only=1)
        eq_(len(target.slides), 1)
        eq_(target.slides[0].shapes.title.text, 'Input.pptx')

    def test_source_with_target(self):
        # Test case to compare target output title.
        pptgen(source=self.input, target=self.output, only=1)
        target = Presentation(self.output)
        eq_(len(target.slides), 1)
        eq_(target.slides[0].shapes.title.text, 'Input.pptx')

    def test_change_title(self):
        # Title change test case with unicode value.
        text = '高σ高λس►'
        target = pptgen(
            source=self.input, only=1,
            change={                  # Configurations are same as when loading from the YAML file
                'Title 1': {            # Take the shape named "Title 1"
                    'text': text          # Replace its text with new text
                }
            })
        eq_(target.slides[0].shapes.title.text, text)

    def test_text_xml(self):
        # Test case for text xml object
        text = "New Title<text color='#00ff00' bold='True' font-size='14'> Green Bold Text</text>"
        font_size, text_color, pix_to_inch = 12, '#ff0000', 10000
        target = pptgen(
            source=self.input, only=1,
            change={
                'Title 1': {
                    'style': {
                        'color': text_color,
                        'font-size': font_size
                    },
                    'text': text
                }
            })
        eq_(target.slides[0].shapes.title.text, 'New Title Green Bold Text')
        text_shape = self.get_shape(target, 'Title 1')[0]
        total_runs = 2
        # Maximum one paragraph should be there, because entire text area is being changed
        eq_(len(text_shape.text_frame.paragraphs), 1)
        # Maximum two runs should be there, because we are adding two seperate style for texts
        eq_(len(text_shape.text_frame.paragraphs[0].runs), total_runs)

        first_run = text_shape.text_frame.paragraphs[0].runs[0]
        second_run = text_shape.text_frame.paragraphs[0].runs[1]

        eq_('{}'.format(first_run.font.color.rgb), 'FF0000')
        eq_('{}'.format(first_run.text), 'New Title')
        eq_(int(int('{}'.format(first_run.font.size)) / pix_to_inch), font_size - 1)

        second_run_font = 14
        eq_('{}'.format(second_run.font.color.rgb), '00FF00')
        eq_('{}'.format(second_run.text), ' Green Bold Text')
        eq_(int(int('{}'.format(second_run.font.size)) / pix_to_inch), second_run_font - 1)

    def test_replicate_slide(self):
        # Test slide replication.
        data = self.data.groupby('city')
        tmpl = "Region: {{ city }} has Sales: {{ sales }} with Growth: {{ growth }}"
        target = pptgen(
            source=self.input,
            only=3,
            data={'data': data},
            replicate_slide={
                'replicate': True,
                'data': "data['data']",
                'sales-text': {
                    'data': "data[0]",
                    'text': tmpl
                }
            })
        eq_(len(data.groups), len(target.slides))
        slds = target.slides
        tmpl_data = [self.template(tmpl, grp[1].to_dict(orient='records')[0]) for grp in data]
        slide_data = [shp.text for sld in slds for shp in sld.shapes if shp.name == 'sales-text']
        eq_(slide_data, tmpl_data)

    def test_text_style(self):
        # Test case for testing text styles.
        target = pptgen(
            source=self.input,
            only=4,
            replicate_slide={
                'Title 1': {
                    'text': "New title",
                    'style': {
                        'color': '#ff0000'
                    }
                },
                'Text 1': {
                    'text': "New text",
                    'style': {
                        'color': '#00ff00',
                        'bold': True
                    }
                }
            })
        slides = target.slides
        eq_(len(slides), 1)
        name_map = {'Title 1': {'color': 'FF0000', 'text': 'Title 1'},
                    'Text 1': {'color': '00FF00', 'text': 'Text 1'}}
        for shape in slides[0].shapes:
            if shape.name not in ['Title 1', 'Text 1']:
                eq_(shape.text, name_map[shape.name]['text'])
                for paragraph in shape.text_frame.paragraphs:
                    for run in paragraph.runs:
                        eq_('{}'.format(run.font.color.rgb), name_map[shape.name]['color'])

    def test_group_and_image(self):
        # Test case for group objects.
        target = pptgen(
            source=self.input,
            only=5,
            group_test={
                'Group 1': {
                    'Caption': {
                        'text': "New caption"
                    },
                    'Picture': {
                        'image': self.image
                    }
                }
            })
        eq_(len(target.slides), 1)
        grp_shape = self.get_shape(target, 'Group 1')[0]
        for shape in SlideShapes(grp_shape.element, grp_shape):
            if shape.name == 'Caption':
                eq_(shape.text, 'New caption')
            if shape.name == 'Picture':
                with open(self.image, 'rb') as f:
                    blob = f.read()
                eq_(shape.image.blob, blob)

    def test_stack(self):
        # Test case for stack elements.
        data = self.data.groupby('city', as_index=False)['sales', 'growth'].sum()
        data = data.to_dict(orient='records')
        tmpl = "Region: {{ city }} has Sales: {{ sales }} with Growth: {{ growth }}"
        target = pptgen(
            source=self.input,
            only=6,
            data={'data': data},
            stack_shapes={
                'TextBox 1': {
                    'data': "data['data']",
                    'stack': 'vertical',
                    'margin': 0.10,
                    'text': tmpl
                }
            })
        stacked_shapes = self.get_shape(target, 'TextBox 1')
        eq_(len(target.slides), 1)
        eq_(len(stacked_shapes), len(data))
        contents = [shape.text for shape in stacked_shapes]
        template_data = [self.template(tmpl, item) for item in data]
        eq_(contents, template_data)

    def test_replace(self):
        # Test case for replace command.
        target = pptgen(
            source=self.input, only=7,
            change={
                'TextBox 1': {
                    'replace': {
                        "Old": "New",
                        "Title": "Heading"
                    }
                }
            })
        eq_(len(target.slides), 1)
        txt_box = self.get_shape(target, 'TextBox 1')[0]
        ok_(txt_box.has_text_frame)
        eq_(txt_box.text, 'New Heading')

    def test_css(self):
        # Test case for `css` command.
        pix_to_inch = 10000
        opacity_constant = 100000
        width, height, top, left, opacity_val = 200, 200, 100, 50, 0.1
        target = pptgen(
            source=self.input, only=8,
            change={
                'Rectangle 1': {
                    'css': {
                        'style': {
                            'opacity': opacity_val,
                            'color': '#ff0000',
                            'fill': '#ffff00',
                            'stroke': '#00ff00',
                            'width': width,
                            'height': height,
                            'left': left,
                            'top': top
                        }
                    }
                }
            })
        eq_(len(target.slides), 1)
        shape = self.get_shape(target, 'Rectangle 1')[0]
        opacity = shape.fill.fore_color._xFill.srgbClr.xpath('./a:alpha')[0].values()[0]
        eq_(shape.top, top * pix_to_inch)
        eq_(shape.left, left * pix_to_inch)
        eq_(shape.width, width * pix_to_inch)
        eq_(shape.height, height * pix_to_inch)
        eq_(opacity_val, float(opacity) / opacity_constant)
        eq_('{}'.format(shape.fill.fore_color.rgb), 'FFFF00')
        eq_('{}'.format(shape.line.fill.fore_color.rgb), '00FF00')

    def test_table(self):
        # Function to test `table` command.
        target = pptgen(
            source=self.input, only=9,
            data={'data': self.data},
            change={
                'Table 1': {
                    'table': {
                        'data': 'data["data"]'
                    }
                }
            })
        eq_(len(target.slides), 1)
        shape = self.get_shape(target, 'Table 1')[0]
        eq_(len(shape.table.rows), len(self.data) + 1)
        eq_(len(shape.table.columns), len(self.data.columns))
        columns = []
        table_data = {}
        for row_num, row in enumerate(shape.table.rows):
            for col_num, cell in enumerate(row.cells):
                txt = cell.text_frame.text
                if row_num == 0:
                    columns.append(txt)
                else:
                    if columns[col_num] not in table_data:
                        table_data[columns[col_num]] = []
                    txt = np.nan if txt == 'nan' else txt
                    table_data[columns[col_num]].append(txt)

        columns = sorted(columns)
        eq_(sorted(list(self.data.columns)), columns)
        original_data = self.data[columns].sort_values(by=columns).reset_index(drop=True)
        table_data = pd.DataFrame(table_data)[columns]
        eq_(len(self.data), len(table_data))
        # Converting data types of table data. All columns will have `object` datatype.
        for col in columns:
            table_data[col] = table_data[col].astype(original_data[col].dtype.name)
        table_data = table_data.sort_values(by=columns).reset_index(drop=True)
        # Comparinig `dataframe` from table with original `dataframe`
        assert_frame_equal(table_data, original_data, check_names=True)

    def test_change_chart(self):
        # Test case for all native charts charts.
        slidenumbers = AttrDict(Bar_Chart=2, Column_Chart=10, Line_Chart=11, Area_Chart=12,
                                Scatter_Chart=13, Bubble_Chart=14, Bubble_Chart_3D=15,
                                Radar_Chart=16, Donut_Chart=17, Pie_Chart=18)
        for chart_name, slidenumber in slidenumbers.items():
            # Replacing `_` with a white space. Because chart names in input slides contains
            # spaces not `_`.
            chart_name = chart_name.replace('_', ' ')
            if chart_name in ['Pie Chart', 'Donut Chart']:
                data = self.data.groupby('city', as_index=False)['sales'].sum()
                series = ['sales']
            else:
                data = self.data.groupby('city', as_index=False)['sales', 'growth'].sum()
                series = ['growth', 'sales']
            rule = {
                chart_name: {
                    'chart': {
                        'data': "data['data']",
                        'x': 'city',
                    }
                }
            }
            target = self.draw_chart(slidenumber, data, rule)
            shape = self.get_shape(target, chart_name)[0]
            self.check_chart(shape, data, series)

    def test_treemap(self):
        # Test case for treemap.
        target = pptgen(
            source=self.input, only=19,
            data={'data': self.data},
            drawtreemap={
                'Treemap Rectangle': {
                    'treemap': {
                        'data': 'data["data"]',
                        'keys': ['city'],
                        'values': "{'sales': 'sum', 'growth': 'sum'}",
                        'size': {'function': 'lambda v: v["sales"]'},
                        'sort': {
                            'function': 'lambda v: v.sort_values(by=["sales"], ascending=False)'
                        },
                        'color': {
                            'function': 'lambda v: _color.gradient(v["growth"]/100, _color.RdYlGn)'
                        },
                        'text': {
                            'function': "lambda v: '{}'.format(v['city'])"
                        }
                    }
                }
            })
        data = self.data.groupby('city', as_index=False).agg({'sales': 'sum', 'growth': 'sum'})
        # Sorting as per treemap logic in chart and taking a subset to compare with
        # chart data
        data = data.sort_values(by=['sales'], ascending=False)[['city']]
        data = data.reset_index(drop=True)
        # Only one slide should be there
        eq_(len(target.slides), 1)
        rects = 0
        text, width = [], []
        for shape in target.slides[0].shapes:
            if shape.shape_type == MSO_SHAPE.RECTANGLE:
                # Counting the number of available rectangles in treemap chart
                rects += 1
                # Gettiing text as per treemap draw logic
                text.append(shape.text)
                # Getting rectangles with
                width.append(shape.width)
        # Creating a new dataframe from treemap chart
        treemapdata = pd.DataFrame({'city': text, 'sales': width})
        # Treemap data should to exactly in same order as per data
        assert_frame_equal(data, treemapdata[['city']], check_names=True)

    def test_horizontal_vertical_bullet_chart(self):
        # Test case for horizontal and vertical bullet chart
        default_size = 10000
        change_data = [
            {
                'text': {'function': "lambda v: '%.1f' % v"},
                'poor': 20,
                'slidenumber': 20,
                'shapename': 'Bullet Rectangle Horizontal',
                'orient': 'horizontal'
            },
            {
                'text': False,
                'poor': 0,
                'shapename': 'Bullet Rectangle Vertical',
                'orient': 'vertical',
                'slidenumber': 21
            }
        ]

        input_rect = Presentation(self.input)
        for update_data in change_data:
            # Getting required param from config to compare with output
            orient = update_data['orient']
            shpname = update_data['shapename']
            slidenumber = update_data['slidenumber']
            # Getting shape name
            shapes = input_rect.slides[slidenumber - 1].shapes
            _shp = [shape for shape in shapes if shape.name == shpname][0]
            # width, height = _shp.width, _shp.height
            height = _shp.height if orient == 'horizontal' else _shp.width
            width = _shp.width if orient == 'horizontal' else _shp.height
            lo, hi = 0, self.data["sales"].max()
            good = 100
            target = pptgen(
                source=self.input, only=slidenumber,
                data={'data': self.data},
                draw_bullet={
                    shpname: {
                        'bullet': {
                            'data': 'data["data"]["sales"].ix[0]',
                            'poor': update_data['poor'],
                            'good': good,
                            'target': 'data["data"]["sales"].max()',
                            'average': 'data["data"]["sales"].mean()',
                            'orient': orient,
                            'gradient': 'Oranges',
                            'text': update_data['text']
                        }
                    }
                })
            eq_(len(target.slides), 1)
            textboxes, rectangles = 0, 0
            rects_width, rects_height = [], []
            _average = self.data["sales"].mean()
            _data = self.data["sales"].ix[0]
            for rectdata in [good, _average, update_data['poor'], _data]:
                if rectdata:
                    shp_width = int(((rectdata - lo) / (hi - lo)) * width)
                    rects_width.append(shp_width if orient == 'horizontal' else height)
                    rects_height.append(height if orient == 'horizontal' else shp_width)

            # Removing and updatiing actual data point's height
            if orient == 'horizontal':
                rects_height.pop(-1)
                rects_height.append(int(height / 2.0))
            if orient == 'vertical':
                rects_width.pop(-1)
                rects_width.append(int(height / 2.0))
            # Adding target's width and height
            rects_height.append(default_size if orient == 'vertical' else height)
            rects_width.append(default_size if orient == 'horizontal' else height)

            rects_width_from_output, rects_height_from_output = [], []
            for shape in target.slides[0].shapes:
                if shape.name != 'Title 1':
                    if shape.shape_type == MSO_SHAPE_TYPE.TEXT_BOX:
                        textboxes += 1
                    elif shape.shape_type == MSO_SHAPE.RECTANGLE:
                        rectangles += 1
                        rects_width_from_output.append(shape.width)
                        rects_height_from_output.append(shape.height)
            # Comapring number of text boxes to be shown
            total_text_boxes = 2 if update_data['text'] else 0
            eq_(textboxes, total_text_boxes)
            # Comapring number of rectangle shapes
            total_rects = 5 if update_data['poor'] else 4
            eq_(rectangles, total_rects)
            # Comparing rectangle's height
            eq_(rects_height_from_output, rects_height)
            # Comparing rectangle's width
            eq_(rects_width_from_output, rects_width)

    def test_heatgrid(self):
        # Test case for heatgrid
        pix_to_inch = 10000
        default_margin, cell_width, cell_height, leftmargin, font = 5, 60, 50, 0.20, 14
        data = self.data.groupby(
            ['देश', 'city'], as_index=False).agg({'sales': 'sum'})
        target = pptgen(
            source=self.input, only=22,
            data={'data': data},
            drawheatgrid={
                'Heatgrid Rectangle': {
                    'heatgrid': {
                        'data': 'data["data"]',
                        'row': 'देश',
                        'column': 'city',
                        'value': 'sales',
                        'text': True,
                        'left-margin': leftmargin,
                        'cell-width': cell_width,
                        'cell-height': cell_height,
                        'na-text': 'NA',
                        'na-color': '#cccccc',
                        'style': {
                            'gradient': 'RdYlGn',
                            'font-size': font,
                            'text-align': 'center'
                        }
                    }
                }
            })
        eq_(len(target.slides), 1)
        total_rects = len(data['देश'].unique()) * len(data['city'].unique())
        total_txt = total_rects + len(data['देश'].unique()) + len(data['city'].unique())
        rects_count, textboxes = 0, 0
        for shape in target.slides[0].shapes:
            if shape.name != 'Title 1':
                if shape.shape_type == MSO_SHAPE_TYPE.TEXT_BOX:
                    textboxes += 1
                    ok_(shape.has_text_frame)
                    font_size = int(shape.text_frame.paragraphs[0].runs[0].font.size / pix_to_inch)
                    eq_(font_size, font - 1)
                    ok_(shape.text_frame.paragraphs[0].alignment == PP_ALIGN.CENTER)
                elif shape.shape_type == MSO_SHAPE.RECTANGLE:
                    rects_count += 1
                    eq_(shape.width, (cell_width - default_margin - default_margin) * pix_to_inch)
                    eq_(shape.height, (cell_height - default_margin) * pix_to_inch)
        eq_(total_rects, rects_count)
        eq_(total_txt, textboxes)

    def test_sankey(self):
        # Test case for sankey
        shpname = 'Sankey Rectangle'
        slidenumber = 23
        input_shapes = Presentation(self.input).slides[slidenumber - 1].shapes
        width = [shape for shape in input_shapes if shape.name == shpname][0].width
        groups = ['देश', 'city', 'product']
        order = {'function': "lambda g: g['sales'].sum()"}
        text = {'function': "lambda g: g.apply(lambda x: x.name)"}
        color = {'function': "lambda g: _color.gradient(g['growth'].sum(), _color.RdYlGn)"}
        data = self.data.fillna(0)
        target = pptgen(
            source=self.input, only=slidenumber,
            data={'data': data},
            drawsankey={
                shpname: {
                    'sankey': {
                        'data': 'data["data"]',
                        'sort': True,
                        'groups': groups,
                        'color': color,
                        'text': text,
                        'order': order
                    }
                }
            })
        eq_(len(target.slides), 1)

        total_cust_shapes, get_rect_order, get_rect_width = 0, [], []
        grp_order = "lambda g: g['sales'].sum()"

        for index, grp in enumerate(groups):
            grpobj = data.groupby(grp)
            frame = pd.DataFrame({'size': grpobj[grp].count(), 'seq': eval(grp_order)(grpobj)})
            frame['width'] = frame['size'] / float(frame['size'].sum()) * width
            frame = frame.sort_values(by=['seq'])
            get_rect_width.extend([int(i) for i in frame['width'].tolist()])
            get_rect_order.extend(list(frame.index))
            if index < len(groups) - 1:
                grpby = [groups[index], groups[index + 1]]
                total_cust_shapes += len(data.groupby(grpby, as_index=False)['sales'].sum())

        rects_count, cust_shape_count, rect_order, rect_width = 0, 0, [], []
        for shape in target.slides[0].shapes:
            if shape.name != 'Title 1':
                # Custom shapes count
                if len(shape.element.xpath('.//a:custGeom')):
                    cust_shape_count += 1
                # Rectangles count
                elif shape.shape_type == MSO_SHAPE.RECTANGLE:
                    rects_count += 1
                    rect_order.append(shape.text)
                    rect_width.append(shape.width)
        # Comparing number of rectangles
        eq_(len(get_rect_order), rects_count)
        # Comparing rectangle's plot order
        eq_(get_rect_order, rect_order)
        # Comparing rectangle's width
        eq_(get_rect_width, rect_width)
        # Comparing custom shape's count
        eq_(total_cust_shapes, cust_shape_count)

    def test_calendarmap(self):
        # Test case for calendarmap
        periods, slidenumber, label = 150, 24, 40
        shapes = Presentation(self.input).slides[slidenumber - 1].shapes
        shp = [shape for shape in shapes if shape.name == 'Calendar Rectangle'][0]
        labels = [[0, label, 0], [0, label, label]]
        pix_to_inch, weekstart, width, maxrange = 10000, 6, 34, 100.0
        data = pd.DataFrame({'date': pd.date_range('1/1/2017', periods=periods, freq='D')})
        data['column'] = data['date'].apply(lambda x: random.uniform(1.0, maxrange))
        data = data.sort_values(by=['date']).set_index('date')

        for i in range(len(labels[0])):
            left, top = labels[0][i], labels[1][i]
            target = pptgen(
                source=self.input, only=slidenumber,
                data={'data': data},
                drawcalendar={
                    'Calendar Rectangle': {
                        'calendarmap': {
                            'data': 'data["data"]["column"]',
                            'width': width,
                            'weekstart': weekstart,
                            'label_left': left,
                            'label_top': top,
                            'text-color': '#000000',
                            'startdate': 'data.index[0]'
                        }
                    }
                })
            eq_(len(target.slides), 1)
            cell_count = 0
            compare_text = []
            texts = ['%02d' % (txt.day) for txt in data.index]
            leftpx, toppx = left * pix_to_inch, top * pix_to_inch
            leftrect, toprect = 0, 0

            scaledata = pd.Series(data['column']).replace([pd.np.inf, -pd.np.inf], pd.np.nan)
            week = 7
            weekly_mean, weekday_mean = pd.Series(), pd.Series()
            if top:
                rng = range(-weekstart, len(scaledata) + week, week)
                weekly_mean = pd.Series([scaledata[max(0, x):x + week].mean() for x in rng])
            if left:
                _rng = [scaledata[(x - weekstart) % week::week].mean() for x in range(week)]
                weekday_mean = pd.Series(_rng)
            for shape in target.slides[0].shapes:
                if shape.name != 'Title 1':
                    if shape.shape_type == MSO_SHAPE.RECTANGLE:
                        cell = shape.width == shape.height == width * pix_to_inch
                        if cell and shape.left > shp.left + leftpx and shape.top > shp.top + toppx:
                            cell_count += 1
                            compare_text.append(shape.text)
                        # Counting top bar chart rectangles
                        elif shape.name == 'top bar chart rect':
                            toprect += 1
                        # Counting left bar chart rectangles
                        elif shape.name == 'left bar chart rect':
                            leftrect += 1
            # Comparing number of cells in calendarmap
            eq_(cell_count, len(data))
            # Comparing text's order(which is day)
            eq_(texts, compare_text)
            # Comparing left bar chart's rectangle count, if left padding is defined
            eq_(toprect, len(weekly_mean.dropna()))
            # Comparing top bar chart's rectangle count, if top padding is defined
            eq_(leftrect, len(weekday_mean.dropna()))

    @classmethod
    def tearDown(cls):
        # Teardown classmethod.
        if os.path.exists(cls.output):
            os.remove(cls.output)
