module WReader
extend self

  class << self
    attr_accessor :database_dir, :document_dir
  end
  self.database_dir = "database"
  self.document_dir = "pdfs"

end