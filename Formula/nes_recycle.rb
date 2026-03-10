class NesRecycle < Formula
  include Language::Python::Virtualenv

  desc "CLI tool for previewing and submitting the Nespresso recycling pickup form over HTTP"
  homepage "https://github.com/rioriost/homebrew-nes_recycle"
  url "https://files.pythonhosted.org/packages/61/a9/77b5d59843fb70f1a4193cb6f9d1829449ef7dda3ba1450a0fd193b90559/nes_recycle-0.0.3.tar.gz"
  sha256 "744e38972bf9d758d6e181ba8444eb817fea49651e63b0bf8342eb4d83d98746"
  license "MIT"

  depends_on "python@3.14"

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "usage", shell_output("#{bin}/nes_recycle --help")
  end
end
