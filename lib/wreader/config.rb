module WReader
extend self

  class << self
    attr_accessor :database_dir, :document_dir
  end
  self.document_dir = "pdfs"
  
  self.database_engine = WReader::SQLite3
  self.database_dir = "database"

  def get_database(*args)
    database_engine.new(*args)
  end

end