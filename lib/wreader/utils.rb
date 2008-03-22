module WReader
extend self

  def error(cgi, msg)
    cgi.out("status" => "SERVER_ERROR"){
      cgi.html{ cgi.body{
        cgi.h2{
          "ERROR in
          #{ CGI.escapeHTML cgi.script_name.to_s }
          #{ CGI.escapeHTML cgi.query_string.to_s }"
        } +
        cgi.p { msg }
      } }
    }
    exit
  end

  def print_profile(times)
    return if times.empty?
    prev = times[0][1]
    times.each{|t|
      STDERR.puts("#{interval_bar(prev, t[1])} #{t[0]}")
      prev = t[1]
    }
    STDERR.puts("Total time: %.3fms" % [(times[-1][1] - times[0][1]) * 1000])
    STDERR.puts
  end

  def interval_bar(a, b)
    a ||= b
    ms = (b - a) * 1000
    "[#{("#"*([16, (ms*2).round].min)).rjust(16)}] %.3fms" % [ms]
  end

end
