#!/usr/bin/ruby

=begin
  reader.cgi - Read documents on the web server

  Copyright (C) 2007  Ilmari Heikkinen

  This program is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation; either version 3 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with this program; if not, write to the Free Software
  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

  http://www.gnu.org/copyleft/gpl.html
=end

# reader.cgi
# item=item_path (2007/10-10-Thu/foo.pdf)
# page=page_num (4)

$KCODE = 'u'

GC.disable # no need to GC on a CGI script

times = []
times << ['begin', Time.now.to_f]

require 'wreader'
require 'cgi'
require 'uri'

times << ['loaded libs', Time.now.to_f]

cgi = CGI.new('html3')

unless cgi.has_key?('page')
  head = cgi.header(
    "status" => "MOVED",
    "location" => 'reader.cgi?' + ENV['QUERY_STRING'] + '&page=1'
  )
  cgi.print(head)
  exit
end

filename = cgi['item'].to_s

WReader.assert_filename(cgi, filename)
times << ['assert filename', Time.now.to_f]

reader = WReader::Reader.new(filename)
times << ['init WReader::Reader', Time.now.to_f]

metadata = reader.metadata
page = [cgi['page'].to_i, 1].max

pg = metadata['Doc.PageCount']
WReader.error(cgi, "Failed to get page count of document.", filename, page) if pg.nil?
pages = [1, pg.to_i].max

page_text = reader.get_page_text(page)
times << ['page text', Time.now.to_f]

uri_pre = "reader.cgi?item=#{URI.escape(filename)}&page="
page_pre = "convert.cgi?type=image&item=#{URI.escape(filename)}&page="

short_pages_div = %Q(
        <div class="short_pages" id="top_navigation">
          #{
            if page > 1
              %Q(<a href="#{uri_pre}#{page-1}">&larr;prev</a>)
            else
              "&larr;prev"
            end
          }
          #{
            if page < pages
              %Q(<a href="#{uri_pre}#{page+1}">next&rarr;</a>)
            else
              "next&rarr;"
            end
          }
          <span id="page_list">
          [ #{
            if page == 12
              %Q(<a href="1">1</a> )
            elsif page > 12
              %Q(<a href="#{uri_pre}1">1</a> <a href="#pagelist">...</a> )
            end
          }
          #{
            sp = [1, page-10].max
            (sp..[sp+20, pages].min).map{|i|
              if i == page
                %Q(<span class="current">#{i}</span>)
              else
                %Q(<a href="#{uri_pre}#{i}">#{i}</a>)
              end
            }.compact.join(" ")
          }
          #{
            if page == pages-11
              %Q( <a href="#{uri_pre}#{pages}">#{pages}</a>)
            elsif page < pages-10
              %Q(<a href="#pagelist">...</a> <a href="#{uri_pre}#{pages}">#{pages}</a>)
            end
          } ]
          </span>
        </div>
)
pages_div = %Q(
        <div class="pages" id="all_pages">
        <a name="pagelist"></a>
          #{
            plen = pages.to_s.length
            (1..pages).map{|i|
              if i == page
                %Q(<span class="current">#{i.to_s.rjust(plen,"0")}</span>)
              else
                %Q(<a href="#{uri_pre}#{i}">#{i.to_s.rjust(plen,"0")}</a>)
              end
            }.compact.join(" ")
          }
        </div>
)

current_page = %Q(
        <div id="current_page">
          #{
            unless page == pages
              %Q(<a href="#{uri_pre}#{(page % pages) + 1}">)
            end
          }<img style="border:1px solid black;" alt="Image of page #{page}" src="#{page_pre}#{page}">#{
            unless page == pages
              "</a>"
            end
          }
        </div>
)

page_thumbs = %Q(
        <div id="page_thumbs">
        </div>
)

thumb_size = 128
thumb_dims = reader.dims(thumb_size)
thumb_text = %Q(
          #{
            pgu = "convert.cgi?type=image&item=#{URI.escape(filename)}&size=#{thumb_size}&page="
            sp = [1, page-2].max
#             (sp..[sp+4, pages].min)
            (1..pages).map{|i|
              if i == page
                %Q(<span id="current_page_thumb"><img src="#{pgu}#{i}"><br>#{i}</span>)
              else
                %Q(<a href="#{uri_pre}#{i}"><img src="#{pgu}#{i}"><br>#{i}</a>)
              end
            }.compact.join("<br>")
          }
)

text = %Q(
  <div id="page_text" style="display:none;">
    #{
      CGI.escapeHTML(page_text).gsub("\n", "<br>")
    }
  </div>
)


item_metadata = %Q(
  <div id="metadata">
    <form>
      <div class="item_metadata">
        <p><a href="#{URI.escape(filename)}">download</a>
        (#{
          if filename.split(".").last.downcase != 'pdf'
            %Q(<a href="convert.cgi?type=pdf&item=#{URI.escape(filename)}">PDF</a> | )
          end
        }<a href="convert.cgi?type=mp3&item=#{URI.escape(filename)}">MP3</a>
        | <a href="convert.cgi?type=txt&item=#{URI.escape(filename)}">text</a>)
        </p>
      </div>
      <h3>Filename</h3>
      <p>
        #{CGI.escapeHTML( File.basename(filename) )}
      </p>
      <h3>Title</h3>
      <p>
        #{CGI.escapeHTML( metadata['Doc.Title'].to_s )}
      </p>
      <h3>Author(s)</h3>
      <p>
        #{CGI.escapeHTML( metadata['Doc.Author'].to_s )}
      </p>
      <h3>Date</h3>
      <p>
        #{CGI.escapeHTML( metadata['Doc.Modified'].to_s )}
      </p>
      #{"<h3>Words</h3><p>#{metadata['Doc.WordCount']}</p>" if metadata['Doc.WordCount']}
      <h3>Pages</h3>
      <p>
        #{metadata['Doc.PageCount']}
      </p>
      <h3>Page size</h3>
      <p>
        #{metadata['Image.Width'].to_f.round}x#{metadata['Image.Height'].to_f.round}#{metadata['Image.DimensionUnit']}
        #{metadata['Doc.PageSizeName'] ? "(#{metadata['Doc.PageSizeName']})" : ""}
      </p>
      <h3>Description</h3>
      <p>
        #{CGI.escapeHTML(metadata['Doc.Description'] || "")}
      </p>
    </form>
  </div>
)

stylesheet = %Q(
  <style type="text/css">
    a {
      color: #248;
    }
    #page_list a {
      padding-left: 1px;
      padding-right: 1px;
    }
    a:visited {
      color: #422;
    }
    a:hover {
      color: #48a;
    }
    #top_navigation span {
      padding-left:1px;
      padding-right: 1px;
    }
    #page_thumbs {
      text-align: center;
      width: 160px;
      left: 1px;
      top: 0px;
      height: 100%;
      position: absolute;
      overflow: auto;
    }
    #page_thumbs img {
      margin-top: 4px;
    }
    #current_page_thumb img {
      border:8px solid #48a;
    }
    #current_page_thumb {
      color: #48a;
    }
    #metadata {
      width: 256px;
      float: left;
      margin-left: 8px;
      padding-right: 8px;
      padding-top: 4px;
    }
    .item_metadata {
      font-size: 14px;
    }
    .item_metadata a {
      color: black;
    }
    #metadata p {
      font-size: 14px;
      margin-left: 8px;
      margin-top: 2px;
      min-height: 1.5em;
      float: left;
    }
    #metadata div {
      clear:both;
    }
    #metadata .item_metadata p {
      margin-left: 0px;
    }
    #metadata h3 {
      float: left;
      clear: both;
      margin: 0px;
      font-size: 14px;
      margin-top: 1px;
      font-family: Helvetica, Sans-serif;
    }
    #current_page {
      float: left;
      padding-top: 8px;
      margin-bottom: 16px;
    }
    .current {
      color: white;
      background-color: #48a;
    }
    #citations ul {
      padding-left: 20px;
    }
    #citations li {
      list-style: circle;
      font-size: 11px;
      margin-bottom: 4px;
    }
    .comment {
      font-size: 11px;
      margin-left: 8px;
      margin-bottom: 4px;
    }
  </style>
)
script = %Q(
  <script type="text/javascript">
    var ap = document.getElementById('all_pages')
    var tn = document.getElementById('page_list')
    ap.style.borderTop = '1px dotted black'
    ap.style.marginTop = '4px'
    ap.style.marginBottom = '4px'
    ap.style.paddingTop = '4px'
    ap.parentNode.removeChild(ap)
    ap.style.display = 'none'
    links = document.getElementsByTagName('a')
    for (var i=0; i<links.length; i++) {
      var a = links[i]
      if (a.getAttribute('href') == '#pagelist') {
        a.onclick = function(ev) {
          ap.style.display = (ap.style.display == 'none') ? 'block' : 'none'
          return false
        }
      }
    }
    var pt = document.getElementById('page_text')
    var link = document.createElement('a')
    link.innerHTML = 'Toggle page text'
    link.href = '#'
    link.onclick = function(ev) {
      pt.style.display = (pt.style.display == 'none') ? 'block' : 'none'
      return false
    }
    pt.style.borderTop = '1px dotted black'
    pt.style.marginTop = '4px'
    pt.style.paddingTop = '4px'
    tn.appendChild(link)
    tn.appendChild(ap)
    var thumbs = document.getElementById('page_thumbs')
    thumbs.innerHTML = #{thumb_text.dump}
    var ct = document.getElementById('current_page_thumb')
    if (ct && ct.previousSibling && ct.previousSibling.previousSibling && ct.previousSibling.previousSibling.previousSibling)
      thumbs.scrollTop = ct.previousSibling.previousSibling.previousSibling.offsetTop
    var c = document.getElementById('content')
    var s = c.style
    s.position = 'absolute'
    s.paddingLeft = '4px'
    s.left = '161px'
    s.top = '0px'
    s.right = '0px'
    s.height = '100%'
    s.overflow = 'auto'
  </script>
)

content = cgi.html{
  cgi.head{
    cgi.title{ (metadata['Doc.Title'] || File.basename(filename)) + " - page #{page}" } +
    stylesheet
  } +
  cgi.body{
    cgi.div("id"=>'content'){
      short_pages_div +
      text +
      current_page +
      item_metadata +
      pages_div
    } +
    page_thumbs +
    script
  }
}
head = cgi.header(
  "type" => "text/html",
  "length" => content.size,
  "status" => "OK",
  "Connection" => "close",
  "expires" => Time.now + (86400 * 365),
  "Last-modified" => File.mtime(filename).httpdate
)
cgi.print(head)
cgi.print(content)
times << ['create HTML', Time.now.to_f]

WReader.print_profile(times)


