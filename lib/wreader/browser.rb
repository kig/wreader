require 'wreader/db'

module WReader


  class Browser
    attr_reader :db

    def initialize(database=WReader.get_database)
      @db = database
    end

    def items
      files = Dir[File.join(WReader.document_dir, "*")]
      files.delete_if{|f| f =~ /\-temp\.pdf$/ }
      files.map{|fn| Item.new(*fn) }
    end

  end


  class Item
    attr_reader :path, :title

    def initialize(path, title=File.basename(path))
      @path = path
      @title = title || File.basename(path)
    end

  end


end
