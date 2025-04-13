NAME
    New-BurntToastNotification

SYNOPSIS
    Creates and displays a Toast Notification.

SYNTAX
    New-BurntToastNotification [-Text <String[]>] [-Column <AdaptiveSubgroup[]>] [-AppId `<String>`] [-AppLogo `<String>`]
    [-HeroImage `<String>`] [-Sound `<String>`] [-Header `<ToastHeader>`] [-ProgressBar <AdaptiveProgressBar[]>]
    [-UniqueIdentifier `<String>`] [-DataBinding `<Hashtable>`] [-ExpirationTime `<DateTime>`] [-SuppressPopup]
    [-CustomTimestamp `<DateTime>`] [-ActivatedAction `<ScriptBlock>`] [-DismissedAction `<ScriptBlock>`] [-WhatIf]
    [-Confirm] [`<CommonParameters>`]

    New-BurntToastNotification [-Text <String[]>] [-Column <AdaptiveSubgroup[]>] [-AppId`<String>`] [-AppLogo `<String>`]
    [-HeroImage `<String>`] -Sound `<String>` -Button <IToastButton[]> [-Header `<ToastHeader>`] [-ProgressBar
    <AdaptiveProgressBar[]>] [-UniqueIdentifier `<String>`] [-DataBinding `<Hashtable>`] [-ExpirationTime `<DateTime>`]
    [-SuppressPopup] [-CustomTimestamp `<DateTime>`] [-ActivatedAction `<ScriptBlock>`] [-DismissedAction `<ScriptBlock>`]
    [-WhatIf] [-Confirm] [`<CommonParameters>`]

    New-BurntToastNotification [-Text <String[]>] [-Column <AdaptiveSubgroup[]>] [-AppId`<String>`] [-AppLogo `<String>`]
    [-HeroImage `<String>`] -Sound `<String>` -SnoozeAndDismiss [-Header `<ToastHeader>`] [-ProgressBar
    <AdaptiveProgressBar[]>] [-UniqueIdentifier `<String>`] [-DataBinding `<Hashtable>`] [-ExpirationTime `<DateTime>`]
    [-SuppressPopup] [-CustomTimestamp `<DateTime>`] [-ActivatedAction `<ScriptBlock>`] [-DismissedAction `<ScriptBlock>`]
    [-WhatIf] [-Confirm] [`<CommonParameters>`]

    New-BurntToastNotification [-Text <String[]>] [-Column <AdaptiveSubgroup[]>] [-AppId`<String>`] [-AppLogo `<String>`]
    [-HeroImage `<String>`] -Silent -Button <IToastButton[]> [-Header `<ToastHeader>`] [-ProgressBar
    <AdaptiveProgressBar[]>] [-UniqueIdentifier `<String>`] [-DataBinding `<Hashtable>`] [-ExpirationTime `<DateTime>`]
    [-SuppressPopup] [-CustomTimestamp `<DateTime>`] [-ActivatedAction `<ScriptBlock>`] [-DismissedAction `<ScriptBlock>`]
    [-WhatIf] [-Confirm] [`<CommonParameters>`]

    New-BurntToastNotification [-Text <String[]>] [-Column <AdaptiveSubgroup[]>] [-AppId`<String>`] [-AppLogo `<String>`]
    [-HeroImage `<String>`] -Silent -SnoozeAndDismiss [-Header `<ToastHeader>`] [-ProgressBar <AdaptiveProgressBar[]>]
    [-UniqueIdentifier `<String>`] [-DataBinding `<Hashtable>`] [-ExpirationTime `<DateTime>`] [-SuppressPopup]
    [-CustomTimestamp `<DateTime>`] [-ActivatedAction `<ScriptBlock>`] [-DismissedAction `<ScriptBlock>`] [-WhatIf]
    [-Confirm] [`<CommonParameters>`]

    New-BurntToastNotification [-Text <String[]>] [-Column <AdaptiveSubgroup[]>] [-AppId`<String>`] [-AppLogo `<String>`]
    [-HeroImage `<String>`] -Silent [-Header `<ToastHeader>`] [-ProgressBar <AdaptiveProgressBar[]>] [-UniqueIdentifier
    `<String>`] [-DataBinding `<Hashtable>`] [-ExpirationTime `<DateTime>`] [-SuppressPopup] [-CustomTimestamp `<DateTime>`]
    [-ActivatedAction `<ScriptBlock>`] [-DismissedAction `<ScriptBlock>`] [-WhatIf] [-Confirm] [`<CommonParameters>`]

    New-BurntToastNotification [-Text <String[]>] [-Column <AdaptiveSubgroup[]>] [-AppId`<String>`] [-AppLogo `<String>`]
    [-HeroImage `<String>`] -SnoozeAndDismiss [-Header `<ToastHeader>`] [-ProgressBar <AdaptiveProgressBar[]>]
    [-UniqueIdentifier `<String>`] [-DataBinding `<Hashtable>`] [-ExpirationTime `<DateTime>`] [-SuppressPopup]
    [-CustomTimestamp `<DateTime>`] [-ActivatedAction `<ScriptBlock>`] [-DismissedAction `<ScriptBlock>`] [-WhatIf]
    [-Confirm] [`<CommonParameters>`]

    New-BurntToastNotification [-Text <String[]>] [-Column <AdaptiveSubgroup[]>] [-AppId`<String>`] [-AppLogo `<String>`]
    [-HeroImage `<String>`] -Button <IToastButton[]> [-Header `<ToastHeader>`] [-ProgressBar <AdaptiveProgressBar[]>]
    [-UniqueIdentifier `<String>`] [-DataBinding `<Hashtable>`] [-ExpirationTime `<DateTime>`] [-SuppressPopup]
    [-CustomTimestamp `<DateTime>`] [-ActivatedAction `<ScriptBlock>`] [-DismissedAction `<ScriptBlock>`] [-WhatIf]
    [-Confirm] [`<CommonParameters>`]

DESCRIPTION
    The New-BurntToastNotification function creates and displays a Toast Notification on Microsoft Windows 10.

    You can specify the text and/or image displayed as well as selecting the sound that is played when the Toast
    Notification is displayed.

    You can optionally call the New-BurntToastNotification function with the Toast alias.

PARAMETERS
    -Text <String[]>
        Specifies the text to show on the Toast Notification. Up to three strings can be displayed, the first of which
        will be embolden as a title.

    Required?                    false
        Position?                    named
        Default value                Default Notification
        Accept pipeline input?       false
        Accept wildcard characters?  false

    -Column <AdaptiveSubgroup[]>
        Specifies groups of content (text and images) created via New-BTColumn that are displayed as a column.

    Multiple columns can be provided and they will be displayed side by side.

    Required?                    false
        Position?                    named
        Default value
        Accept pipeline input?       false
        Accept wildcard characters?  false

    -AppId`<String>`
        Specifies the AppId of the 'application' or process that spawned the toast notification.

    Required?                    false
        Position?                    named
        Default value                $Script:Config.AppId
        Accept pipeline input?       false
        Accept wildcard characters?  false

    -AppLogo`<String>`
        Specifies the path to an image that will override the default image displayed with a Toast Notification.

    Required?                    false
        Position?                    named
        Default value
        Accept pipeline input?       false
        Accept wildcard characters?  false

    -HeroImage`<String>`
        Specifies the path to an image that will be used as the hero image on the toast.

    Required?                    false
        Position?                    named
        Default value
        Accept pipeline input?       false
        Accept wildcard characters?  false

    -Sound`<String>`
        Selects the sound to acompany the Toast Notification. Any 'Alarm' or 'Call' tones will automatically loop and
        extent the amount of time that a Toast is displayed on screen.

    Cannot be used in conjunction with the 'Silent' switch.

    Required?                    false
        Position?                    named
        Default value                Default
        Accept pipeline input?       false
        Accept wildcard characters?  false

    -Silent [`<SwitchParameter>`]
        Indicates that the Toast Notification will be displayed on screen without an accompanying sound.

    Cannot be used in conjunction with the 'Sound' parameter.

    Required?                    true
        Position?                    named
        Default value                False
        Accept pipeline input?       false
        Accept wildcard characters?  false

    -SnoozeAndDismiss [`<SwitchParameter>`]
        Adds a default selection box and snooze/dismiss buttons to the bottom of the Toast Notification.

    Required?                    true
        Position?                    named
        Default value                False
        Accept pipeline input?       false
        Accept wildcard characters?  false

    -Button <IToastButton[]>
        Allows up to five buttons to be added to the bottom of the Toast Notification. These buttons should be created
        using the New-BTButton function.

    Required?                    true
        Position?                    named
        Default value
        Accept pipeline input?       false
        Accept wildcard characters?  false

    -Header`<ToastHeader>`
        Specify the Toast Header object created using the New-BTHeader function, for seperation/categorization of
        toasts from the same AppId.

    Required?                    false
        Position?                    named
        Default value
        Accept pipeline input?       false
        Accept wildcard characters?  false

    -ProgressBar <AdaptiveProgressBar[]>
        Specify one or more Progress Bar object created using the New-BTProgressBar function.

    Required?                    false
        Position?                    named
        Default value
        Accept pipeline input?       false
        Accept wildcard characters?  false

    -UniqueIdentifier`<String>`
        A string that uniquely identifies a toast notification. Submitting a new toast with the same identifier as a
        previous toast will replace the previous toast.

    This is useful when updating the progress of a process, using a progress bar, or otherwise correcting/updating
        the information on a toast.

    Required?                    false
        Position?                    named
        Default value
        Accept pipeline input?       false
        Accept wildcard characters?  false

    -DataBinding`<Hashtable>`
        A hashtable that binds strings to keys in a toast notification. In order to update a toast, the original toast
        needs to include a databinding hashtable.

    Required?                    false
        Position?                    named
        Default value
        Accept pipeline input?       false
        Accept wildcard characters?  false

    -ExpirationTime`<DateTime>`
        The time after which the notification is no longer relevant and should be removed from the Action Center.

    Required?                    false
        Position?                    named
        Default value
        Accept pipeline input?       false
        Accept wildcard characters?  false

    -SuppressPopup [`<SwitchParameter>`]
        Bypasses display to the screen and sends the notification directly to the Action Center.

    Required?                    false
        Position?                    named
        Default value                False
        Accept pipeline input?       false
        Accept wildcard characters?  false

    -CustomTimestamp`<DateTime>`
        Sets the time at which Windows should consider the notification to have been created. If not specified the
        time at which the notification was recieved will be used.

    The time stamp affects sorting of notifications in the Action Center.

    Required?                    false
        Position?                    named
        Default value
        Accept pipeline input?       false
        Accept wildcard characters?  false

    -ActivatedAction`<ScriptBlock>`

    Required?                    false
        Position?                    named
        Default value
        Accept pipeline input?       false
        Accept wildcard characters?  false

    -DismissedAction`<ScriptBlock>`

    Required?                    false
        Position?                    named
        Default value
        Accept pipeline input?       false
        Accept wildcard characters?  false

    -WhatIf [`<SwitchParameter>`]

    Required?                    false
        Position?                    named
        Default value
        Accept pipeline input?       false
        Accept wildcard characters?  false

    -Confirm [`<SwitchParameter>`]

    Required?                    false
        Position?                    named
        Default value
        Accept pipeline input?       false
        Accept wildcard characters?  false

    `<CommonParameters>`
        This cmdlet supports the common parameters: Verbose, Debug,
        ErrorAction, ErrorVariable, WarningAction, WarningVariable,
        OutBuffer, PipelineVariable, and OutVariable. For more information, see
        about_CommonParameters (https:/go.microsoft.com/fwlink/?LinkID=113216).

INPUTS
    None
        You cannot pipe input to this function.

OUTPUTS
    None
        New-BurntToastNotification displays the Toast Notification that is created.

NOTES

    I'm*really* sorry about the number of Parameter Sets. The best explanation is:

    * You cannot specify a sound and mark the toast as silent at the same time.
        * You cannot specify SnoozeAndDismiss and custom buttons at the same time.

    -------------------------- EXAMPLE 1 --------------------------

    PS C:\>New-BurntToastNotification

    This command creates and displays a Toast Notification with all default values.

    -------------------------- EXAMPLE 2 --------------------------

    PS C:\>New-BurntToastNotification -Text 'Example Script', 'The example script has run successfully.'

    This command creates and displays a Toast Notification with customized title and display text.

    -------------------------- EXAMPLE 3 --------------------------

    PS C:\>New-BurntToastNotification -Text 'WAKE UP!' -Sound 'Alarm2'

    This command creates and displays a Toast Notification which plays a looping alarm sound and lasts longer than a
    default Toast.

    -------------------------- EXAMPLE 4 --------------------------

    PS C:\>$BlogButton = New-BTButton -Content 'Open Blog' -Arguments 'https://king.geek.nz'

    New-BurntToastNotification -Text 'New Blog Post!' -Button $BlogButton

    This exmaple creates a Toast Notification with a button which will open a link to "https://king.geek.nz" when
    clicked.

    -------------------------- EXAMPLE 5 --------------------------

    PS C:\>$ToastHeader = New-BTHeader -Id '001' -Title 'Stack Overflow Questions'

    New-BurntToastNotification -Text 'New Stack Overflow Question!', 'More details!' -Header $ToastHeader

    This example creates a Toast Notification which will be displayed under the header 'Stack Overflow Questions.'

    -------------------------- EXAMPLE 6 --------------------------

    PS C:\>$Progress = New-BTProgressBar -Status 'Copying files' -Value 0.2

    New-BurntToastNotification -Text 'File copy script running', 'More details!' -ProgressBar $Progress

    This example creates a Toast Notification which will include a progress bar.

    -------------------------- EXAMPLE 7 --------------------------

    PS C:\>New-BurntToastNotification -Text 'Professional Content', 'And gr8 spelling' -UniqueIdentifier 'Toast001'

    New-BurntToastNotification -Text 'Professional Content', 'And great spelling' -UniqueIdentifier 'Toast001'

    This example will show a toast with a spelling error, which is replaced by a second toast because they both shared
    a unique identifier.

RELATED LINKS
