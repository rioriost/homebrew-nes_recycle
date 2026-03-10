class NesRecycle < Formula
  include Language::Python::Virtualenv

  desc "CLI tool for previewing and submitting the Nespresso recycling pickup form over HTTP"
  homepage "https://github.com/rioriost/homebrew-nes_recycle"
  url "https://github.com/rioriost/homebrew-nes_recycle/archive/refs/tags/v0.0.1.tar.gz"
  sha256 "REPLACE_WITH_SOURCE_TARBALL_SHA256"
  license "MIT"

  depends_on "python@3.11"

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "usage", shell_output("#{bin}/nes_recycle --help")
  end
end
