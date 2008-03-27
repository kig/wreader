require 'wreader/db'
require 'wreader/reader'

module WReader


  class Browser
    attr_reader :db

    def initialize(database=WReader.get_database)
      @db = database
    end

    def items
      files = Dir[File.join(WReader.document_dir, "*")].sort
      files.delete_if{|f| f =~ /\-temp\.pdf$/ }
      files.map{|fn| WReader::Reader.new(fn, db) }
    end

  end


end
