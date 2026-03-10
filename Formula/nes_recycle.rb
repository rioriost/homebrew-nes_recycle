class NesRecycle < Formula
  include Language::Python::Virtualenv

  desc "CLI tool for previewing and submitting the Nespresso recycling pickup form over HTTP"
  homepage "https://github.com/rioriost/homebrew-nes_recycle"
  url "https://files.pythonhosted.org/packages/90/ac/847a0c2f5c67394ed9fe60aa1b75aa0da893be9eafe8fff8f2fa752b6cd5/nes_recycle-0.0.2.tar.gz"
  sha256 "6c316827f8325ed393997f0c7d36abcf146abb7562f2d1554ed73913ced10c57"
  license "MIT"

  depends_on "python@3.14"

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "usage", shell_output("#{bin}/nes_recycle --help")
  end
end
