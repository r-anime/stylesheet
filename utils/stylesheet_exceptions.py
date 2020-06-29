"""Stylesheet exception classes."""
from sass import CompileError


class StylesheetException(Exception):
    """The base Stylesheet Exception that all other exception classes extend.
    """

    def __init__(self, message):
        """Construct an instance of StylesheetException."""
        self.message = message

    def __str__(self):
        return self.message


class SassCompileException(StylesheetException):
    """Raised from CompileError when the Sass code contains errors.

    The specific information about errors in included in the error message.
    """

    def __init__(self, compile_error: CompileError, filename):
        """Construct an instance of SassCompileException."""
        message = (f"An error occurred when compiling the Sass file "
        f"{filename}:\n {str(compile_error)}")
        super().__init__(message)
        self.filename = filename


class AuthException(StylesheetException):
    """Raised when authentication via Reddit API fails.

    The error message includes the username used when accessing Reddit API.
    """

    def __init__(self, username):
        """Construct an instance of AuthException."""
        message = f"Failed to authenticate via Reddit API as "
        f"/u/{username}. Check if all the credentials are set correctly."
        super().__init__(message)
        self.username = username


class InvalidImageException(StylesheetException):
    """Raised when format of the loaded image cannot be determined.

    The error message includes the name of the image.
    """

    def __init__(self, name):
        """Construct an instance of InvalidImageException."""
        message = f"Cannot load the contents of the image '{name}'."
        super().__init__(message)
        self.name = name


class ValidationException(StylesheetException):
    """General exception for validation errors.

    The error message includes the list of validation errors.
    """

    def __init__(self, validation_errors):
        """Construct an instance of ValidationException."""
        message = "Validation errors:\n" \
            + ("\n".join("- " + e for e in validation_errors))
        super().__init__(message)
        self.validation_errors = validation_errors


class DataPageMissingException(StylesheetException):
    """Raised when the Data Page is not found.

    The error message includes the relative URL of the Data Page.
    """

    def __init__(self, subreddit_name, data_page_name):
        """Construct an instance of DataPageMissingException."""
        message = "Cannot open the Data Page /r/{}/wiki/{}.".format(
            subreddit_name,
            data_page_name,
        )
        super().__init__(message)
        self.subreddit_name = subreddit_name
        self.data_page_name = data_page_name


class DataPageAccessException(StylesheetException):
    """Raised when the user does not have permissions to edit the Data Page.

    The error message includes the relative URL of the Data Page and the
    username.
    """

    def __init__(self, subreddit_name, data_page_name, username):
        """Construct an instance of DataPageAccessException."""
        self.message = "The currently logged in user /u/{} does not have " \
            "permissions to edit the Data Page /r/{}/wiki/{}.".format(
                username,
                subreddit_name,
                data_page_name,
            )
        super().__init__(message)
        self.subreddit_name = subreddit_name
        self.data_page_name = data_page_name
        self.username = username


class FileSavingException(StylesheetException):
    """Raised from OSError that occurs when saving a file.

    The error message includes the description of the file for a better context
    and the details adopted from the OSError.
    """

    def __init__(self, os_error: OSError, description):
        """Construct an instance of FileSavingException."""
        message = "An error occurred when saving {}:\n{}".format(
            description,
            str(os_error),
        )
        super().__init__(message)
        self.description = description


class FileReadingException(StylesheetException):
    """Raised from OSError that occurs when reading a file.

    The error message includes the description of the file for a better context
    and the details adopted from the OSError.
    """

    def __init__(self, os_error: OSError, description):
        """Construct an instance of FileReadingException."""
        message = "An error occurred when reading {}:\n{}".format(
            description,
            str(os_error),
        )
        super().__init__(message)
        self.description = description


class ImageUploadException(StylesheetException):
    """Raised when upload of an image to Reddit fails.

    The error message includes the path of the image file and additional
    details about the error.
    """

    def __init__(self, path, details):
        """Construct an instance of ImageUploadException."""
        message = f"An error occurred when uploading image '{path}'. {details}"
        super().__init__(message)
        self.path = path
        self.details = details


class StylesheetUpdateException(StylesheetException):
    """Raised when the validation of an updated Stylesheet fails.

    The error message includes the comparison of sizes of the submitted content
    and the content that was retrieved after the update.
    """

    def __init__(self, css_content, saved_css_content):
        """Construct an instance of StylesheetUpdateException."""
        message = "Update of the Stylesheet failed:\n" \
            f"- Submitted content size: {len(css_content)}\n" \
            f"- Retrieved content size: {len(saved_css_content)}"
        super().__init__(message)
        self.css_content = css_content
        self.saved_css_content = saved_css_content


class DataPageUpdateException(StylesheetException):
    """Raised when the validation of an updated Data Page fails.

    The error message includes the comparison of sizes of the submitted content
    and the content that was retrieved after the update.
    """

    def __init__(self, content, saved_content):
        """Construct an instance of DataPageUpdateException."""
        message = "Update of the Data Page failed:\n" \
            f"- Submitted content size: {len(content)}\n" \
            f"- Retrieved content size: {len(saved_content)}"
        super().__init__(message)
        self.content = content
        self.saved_content = saved_content
