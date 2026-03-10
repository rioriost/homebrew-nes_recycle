class NesRecycle < Formula
  include Language::Python::Virtualenv

  desc "CLI tool for previewing and submitting the Nespresso recycling pickup form over HTTP"
  homepage "https://github.com/rioriost/homebrew-nes_recycle"
  url "https://files.pythonhosted.org/packages/d2/98/699e871fdada3da68856cf2b94edfaace70f0a231267205d2d3b2644fd7d/nes_recycle-0.0.1.tar.gz"
  sha256 "073a9d3c842b727bc2f8cbfb4f4b8b3383f5cfcee9f802551069334b3a447043"
  license "MIT"

  depends_on "python@3.11"

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "usage", shell_output("#{bin}/nes_recycle --help")
  end
end
