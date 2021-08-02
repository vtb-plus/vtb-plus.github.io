import argparse
import sys
import bs4
from bs4 import BeautifulSoup, Comment
import datetime
import dateutil.parser
from pathlib import Path


class BliveXML:
    def __init__(self, xml_path: Path) -> None:
        # ---- Base XML
        self.base_xml = self._open_xml(xml_path)
        self.base_xml_out_path = self._gen_output_path(xml_path)
        self.base_start_time = self._start_time(self.base_xml)

    @staticmethod
    def _open_xml(xml_path: Path) -> bs4.BeautifulSoup:
        return BeautifulSoup(open(xml_path, encoding='utf8'), 'xml')

    def open_base_xml(self, xml_path: Path):
        self.base_xml = self._open_xml(xml_path)

    @staticmethod
    def _gen_output_path(input_path: Path) -> Path:
        stem = input_path.stem
        ext = input_path.suffix
        return Path().joinpath(f'{stem}-merged{ext}')

    @staticmethod
    def _start_time(dom: bs4.BeautifulSoup):
        st = dom.i.BililiveRecorderRecordInfo['start_time']
        start_time = dateutil.parser.isoparse(st)
        return start_time

    @staticmethod
    def _update_xml_tag_ts(dom: bs4.BeautifulSoup, dt: float):
        # Update danmuku timestamp.
        #   ts = d['p'].split(',')[0]   time offset (s)
        #   ts = d['p'].split(',')[4]   unix ts     (ms)
        for d in dom.i('d', recursive=False):
            # params list:
            #   progress,mode,fontsize,color,ctime,pool,midHash,id,unknown
            params = d['p'].split(',')
            # get new timestamp
            new_ts = float(params[0]) + dt
            params[0] = f'{new_ts:.7f}'
            # update params list
            d['p'] = ','.join(params)
        # Update gift, sc, guard timestamp.
        #   ts = tag['ts']              time offset (s)
        for tag_name in ['gift', 'sc', 'guard']:
            for tag in dom.i(tag_name, recursive=False):
                new_ts = float(tag['ts']) + dt
                tag['ts'] = f'{new_ts:.7f}'

    def update_xml_ts(self, dom: bs4.BeautifulSoup, new_start_time: datetime.datetime):
        # get dt (s)
        old_st = self._start_time(dom)
        dt = old_st - new_start_time
        # update all things in `<i>` tags
        self._update_xml_tag_ts(dom, dt.total_seconds())
        # set new start time
        dom.i.BililiveRecorderRecordInfo['start_time'] = new_start_time.isoformat()

    @staticmethod
    def _remove_metainfo(dom: bs4.BeautifulSoup):
        meta_tags = [
            'chatserver', 'chatid', 'mission', 'maxlimit', 'state', 'real_name', 'source',
            'BililiveRecorder', 'BililiveRecorderRecordInfo', 'BililiveRecorderXmlStyle'
        ]
        for tag in dom.i(meta_tags):
            tag.decompose()
        # remove comments
        for c in dom.i.findAll(text=lambda text: isinstance(text, Comment)):
            c.extract()

    def add2_base_xml(self, add_xml: bs4.BeautifulSoup):
        self._remove_metainfo(add_xml)
        self.base_xml.i.extend(add_xml.i)

    def merge_xml(self, add_xml_path: Path) -> None:
        new_xml = self._open_xml(add_xml_path)
        self.update_xml_ts(new_xml, self.base_start_time)
        self.add2_base_xml(new_xml)

    @staticmethod
    def _write_xml(dom: bs4.BeautifulSoup, output_path: Path):
        with open(output_path, "w", encoding='utf-8') as file:
            file.write(str(dom))

    def to_file(self, output_path: Path = Path()) -> None:
        if output_path != Path():
            self._write_xml(self.base_xml, output_path)
        else:
            self._write_xml(self.base_xml, self.base_xml_out_path)


def dir_path(spath: str):
    path = Path(spath)
    if path.is_file():
        return path
    else:
        raise NotADirectoryError(path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('XML_file', nargs='+',
                        type=dir_path,
                        help='All XML files')
    parser.add_argument('-o', metavar='merged.xml', nargs='?',
                        default='',
                        dest='output',
                        type=Path,
                        help='Output merged XML file')

    # TODO: add ffmpeg like infile
    #   `ffmpeg -f concat -i 1.txt -c copy or.flv`
    # parser.add_argument('-i', help='ffmpeg infile')

    args = parser.parse_args()
    args.XML_file.sort() 
    print(f'input files: {args.XML_file}')
    print(f'output file: {args.output}')

    BXML = BliveXML(args.XML_file[0])
    for xml in args.XML_file[1:]:
        BXML.merge_xml(xml)
    BXML.to_file(args.output)
