from Utils.logging_support.constants.private_content import PRIVATE_CONTENT_SUMMARY


def private_content_summary(value):
    return PRIVATE_CONTENT_SUMMARY.format(count=len(value or ""))
