class NesRecycle < Formula
  include Language::Python::Virtualenv

  desc "CLI tool for previewing and submitting the Nespresso recycling pickup form over HTTP"
  homepage "https://github.com/rioriost/nes_recycle"
  url "https://github.com/rioriost/nes_recycle/releases/download/0.0.5/nes_recycle-0.0.5.tar.gz"
  sha256 "f089d7ee2c1ee2cebc97d9829255889702a5e5c0977e0ffdc963a0902437b8ce"
  license "MIT"

  depends_on "python@3.14"

  def install
    cd "." do
      virtualenv_install_with_resources
    end
  end

  test do
    system "#{bin}/nes_recycle", "--help"
  end
end
