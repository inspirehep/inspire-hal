# -*- coding: utf-8 -*-
#
# This file is part of INSPIRE.
# Copyright (C) 2014-2019 CERN.
#
# INSPIRE is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# INSPIRE is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with INSPIRE. If not, see <http://www.gnu.org/licenses/>.
#
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as an Intergovernmental Organization
# or submit itself to any jurisdiction.

"""
IMPORTANT This script is a copy/paste of:
https://github.com/inspirehep/inspire-next/issues/2629

It is unreliable and absolutely unmaintainable.
It will be refactored with this user story:
https://its.cern.ch/jira/browse/INSPIR-249

To be run with:
$ /usr/bin/time -v inspirehep hal push
"""

from __future__ import absolute_import, division, print_function

import datetime
import time

from lxml import etree

from invenio_records.models import RecordMetadata
from inspire_hal.core.tei import convert_to_tei
from inspire_hal.core.sword import create, update


def run(limit, yield_amt):
    start = time.time()

    records = RecordMetadata.query.filter(RecordMetadata.json['_export_to'].op('@>')('{"HAL": true}'))

    if limit > 0:
        records = records.limit(limit)

    total = ok = ko = 0
    now = str(datetime.timedelta(seconds=time.time() - start))

    for total, raw_record in enumerate(records.yield_per(yield_amt)):
        if total % 10 == 0:
            now = str(datetime.timedelta(seconds=time.time() - start))

        record = raw_record.json
        if 'Literature' in record['_collections'] or 'HAL Hidden' in record['_collections']:
            try:
                tei = convert_to_tei(record)
            except Exception as e:
                print('EXC TEI: %s %s\n' % (record['control_number'], str(e)))
                ko += 1
                continue

            success = False

            try:
                hal_id = ''
                ids = record.get('external_system_identifiers', [])

                for id_ in ids:
                    if id_['schema'] == 'HAL':
                        hal_id = id_['value']

                if hal_id:
                    rec, idd = tei.encode('utf8'), hal_id.encode('utf8')
                    update(rec, idd)
                    print('UPD: %s %s\n' % (record['control_number'], hal_id))
                else:
                    rec = tei.encode('utf8')
                    receipt = create(rec)
                    print('NEW: %s %s\n' % (record['control_number'], receipt.id))

                success = True

            except Exception as e:
                pass

            if success:
                print('%s) OK %s\n' % (total, record['control_number']))
                ok += 1
            else:

                print(
                    '%s) EXC HAL: %s %s\n' % (total, record['control_number'], format_error(e))
                )
                ko += 1

    return total + 1, now, ok, ko


def format_error(exception):
    try:
        if exception.content:
            root = etree.fromstring(exception.content)
            error = root.findall('.//{http://purl.org/net/sword/error/}verboseDescription')[0].text
            return error
        else:
            return 'Error %d' % exception.response['status']
    except Exception:
        return exception
